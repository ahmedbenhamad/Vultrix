"""Bridge to the real Strix engine.

Launches ``strix --target <t> --non-interactive`` as a subprocess in the Strix
repo, then monitors the run directory it produces under ``strix_runs/`` and
mirrors the results into our DB (status / phase / progress / findings / logs /
report). If the engine isn't configured or the binary can't be found, it falls
back to a built-in simulation so the whole UI still works.

Run-directory contract (Strix telemetry tracer):
- ``vulnerabilities.csv``            id,title,severity,timestamp,file   (streamed per finding)
- ``vulnerabilities/<id>.md``        full finding detail (severity, CVE, description, remediation)
- ``strix.log``                      execution log
- ``run.json``                       final metadata incl. ``status`` (running/completed/failed)
- ``penetration_test_report.md``     executive report (on completion)
"""

import csv
import json
import os
import queue
import re
import shlex
import subprocess  # nosec B404 - launches the configured Strix CLI for authorized scans
import threading
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from app.core import events
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.assessment import Assessment, AssessmentStatus, Finding, Severity
from app.models.log import LogEntry
from app.models.post_ex import PostExEvent, PostExKind
from app.models.report import Report
from app.services import notify_service

PHASES = ["recon", "vuln-assessment", "exploitation", "post-exploitation", "reporting"]

_SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}

# our scan_type -> strix --scan-mode
_SCAN_MODE_MAP = {
    "quick": "quick",
    "standard": "standard",
    "api": "standard",
    "infra": "standard",
    "full": "deep",
    "deep": "deep",
}

# assessment_id -> running subprocess, so /cancel can terminate it
_processes: dict[int, subprocess.Popen] = {}
_cancelled: set[int] = set()

# Concurrency cap: at most N scans actually executing at once; the rest wait
# (status QUEUED) until a slot frees.
_slots = threading.BoundedSemaphore(max(1, settings.STRIX_MAX_CONCURRENT))


# Strip ANSI escape sequences (colors/cursor) that the Strix CLI writes to its log.
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


# ── helpers ──────────────────────────────────────────────────────────────────
def _log(db, assessment_id: int, level: str, message: str) -> None:
    msg = _ANSI_RE.sub("", message)[:4000]
    db.add(LogEntry(level=level, source="engine", message=msg, assessment_id=assessment_id))
    db.commit()
    events.publish(assessment_id, {"type": "log", "level": level, "source": "engine", "message": msg})


def _emit_state(assessment_id: int, *, status: str, phase: str, progress: float,
                findings_count: int = 0, error: str | None = None) -> None:
    events.publish(assessment_id, {
        "type": "state", "status": status, "phase": phase, "progress": progress,
        "findings_count": findings_count, "error": error,
    })


def _add_post_ex(db, assessment_id: int, *, kind: str, title: str,
                 detail: str = "", host: str = "", evidence: str = "") -> None:
    db.add(PostExEvent(
        assessment_id=assessment_id, kind=kind, title=title[:512],
        detail=detail[:4000], host=host[:255], evidence=evidence[:4000],
    ))
    db.commit()
    events.publish(assessment_id, {
        "type": "post_ex", "kind": kind, "title": title, "host": host,
    })
    _log(db, assessment_id, "info", f"Post-exploitation [{kind}]: {title}")


def _phase_for_progress(progress: float) -> str:
    if progress < 20:
        return "recon"
    if progress < 45:
        return "vuln-assessment"
    if progress < 70:
        return "exploitation"
    if progress < 90:
        return "post-exploitation"
    return "reporting"


def _engine_available() -> tuple[bool, str]:
    if settings.STRIX_FORCE_SIMULATION:
        return False, "STRIX_FORCE_SIMULATION is on"
    repo = settings.STRIX_REPO_PATH.strip()
    if not repo:
        return False, "STRIX_REPO_PATH not set"
    if not Path(repo).exists():
        return False, f"STRIX_REPO_PATH does not exist: {repo}"
    return True, ""


# ── public API ───────────────────────────────────────────────────────────────
def _run_with_slot(target, assessment_id: int) -> None:
    """Wait for a concurrency slot (staying QUEUED), then run the scan."""
    acquired = _slots.acquire(blocking=False)
    if not acquired:
        db = SessionLocal()
        try:
            _log(db, assessment_id, "info", "Waiting for a free execution slot…")
        finally:
            db.close()
        _slots.acquire()  # block until a slot frees
    try:
        if assessment_id in _cancelled:
            return
        target(assessment_id)
    finally:
        _slots.release()


def launch(assessment_id: int) -> None:
    ok, reason = _engine_available()
    target = _run_real if ok else _simulate
    if not ok:
        db = SessionLocal()
        try:
            _log(db, assessment_id, "warn", f"Strix engine not used ({reason}); running simulation.")
        finally:
            db.close()
    threading.Thread(target=_run_with_slot, args=(target, assessment_id), daemon=True).start()


def cancel(assessment_id: int) -> None:
    _cancelled.add(assessment_id)
    proc = _processes.get(assessment_id)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:  # noqa: BLE001
            pass


def reconcile_orphans() -> None:
    """On startup, fail assessments orphaned by a dead process.

    A fresh backend process has no live threads for scans that were previously
    RUNNING *or* QUEUED (waiting for a concurrency slot). Both are orphaned — the
    thread that would advance them died with the old process — so without this
    they'd be stuck 'running'/'queued' forever. Mark them failed so the user can
    re-run them explicitly (we intentionally do not auto-relaunch, to avoid
    surprise scans firing on every restart).
    """
    from sqlalchemy import select

    db = SessionLocal()
    try:
        rows = (
            db.execute(
                select(Assessment).where(
                    Assessment.status.in_([AssessmentStatus.RUNNING, AssessmentStatus.QUEUED])
                )
            )
            .scalars()
            .all()
        )
        for a in rows:
            was_queued = a.status == AssessmentStatus.QUEUED
            a.status = AssessmentStatus.FAILED
            a.error = (
                "Interrupted: the backend restarted while this assessment was queued."
                if was_queued
                else "Interrupted: the backend restarted while this assessment was running."
            )
            a.finished_at = datetime.now(UTC)
            db.add(
                LogEntry(
                    level="warn", source="engine",
                    message="Marked failed after backend restart.", assessment_id=a.id,
                )
            )
        if rows:
            db.commit()
    finally:
        db.close()


# ── real engine ──────────────────────────────────────────────────────────────
def _await_run_dir(runs_dir: Path, before: set[str], timeout: int = 90) -> Path | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if runs_dir.exists():
            new = [p for p in runs_dir.iterdir() if p.is_dir() and p.name not in before]
            if new:
                return max(new, key=lambda p: p.stat().st_mtime)
        time.sleep(1)
    return None


def _parse_finding_md(md_path: Path) -> dict[str, str]:
    out = {"cve": "", "description": "", "recommendation": "", "post_exploitation": ""}
    if not md_path.exists():
        return out
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    m = re.search(r"\*\*CVE:\*\*\s*(.+)", text)
    if m:
        out["cve"] = m.group(1).strip()
    desc = re.search(r"##\s*Description\s*\n+(.+?)(?:\n##\s|\Z)", text, re.DOTALL)
    if desc:
        out["description"] = desc.group(1).strip()[:4000]
    rem = re.search(r"##\s*Remediation\s*\n+(.+?)(?:\n##\s|\Z)", text, re.DOTALL)
    if rem:
        out["recommendation"] = rem.group(1).strip()[:4000]
    pex = re.search(r"##\s*Post[- ]?Exploitation\s*\n+(.+?)(?:\n##\s|\Z)", text, re.IGNORECASE | re.DOTALL)
    if pex:
        out["post_exploitation"] = pex.group(1).strip()[:4000]
    return out


def _ingest_findings(db, assessment_id: int, run_dir: Path | None, seen: set[str]) -> None:
    if run_dir is None:
        return
    csv_path = run_dir / "vulnerabilities.csv"
    if not csv_path.exists():
        return
    try:
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8", errors="replace")))
    except OSError:
        return
    a = db.get(Assessment, assessment_id)
    for row in rows:
        vid = (row.get("id") or "").strip()
        if not vid or vid in seen:
            continue
        seen.add(vid)
        detail = _parse_finding_md(run_dir / (row.get("file") or f"vulnerabilities/{vid}.md"))
        _sev = (row.get("severity") or "").strip().lower()
        if a is not None:
            notify_service.notify_finding(a.name, a.target, row.get("title", vid), _sev, detail["cve"] or None)
        db.add(
            Finding(
                assessment_id=assessment_id,
                title=(row.get("title") or "Untitled").strip()[:512],
                severity=_SEVERITY_MAP.get((row.get("severity") or "").strip().lower(), Severity.INFO),
                cve=detail["cve"] or None,
                description=detail["description"] or "Reported by the Strix engine.",
                recommendation=detail["recommendation"],
                evidence=f"See {run_dir.name}/{row.get('file', '')}",
            )
        )
        _log(db, assessment_id, "info", f"Finding: [{row.get('severity')}] {row.get('title')}")
        if detail.get("post_exploitation"):
            _add_post_ex(
                db, assessment_id, kind=PostExKind.SESSION,
                title=f"Post-exploitation via {row.get('title', vid)}"[:512],
                detail=detail["post_exploitation"],
                evidence=f"See {run_dir.name}/{row.get('file', '')}",
            )
    db.commit()


def _ingest_events(assessment_id: int, run_dir: Path | None, offset: int) -> int:
    """Tail the engine's ``events.jsonl`` and republish structured events live.

    This is what makes the web console mirror the Strix CLI: the tracer writes
    one JSON line per thinking message / tool call / agent lifecycle event, and
    we forward each as a typed WS event the frontend renders CLI-style. Returns
    the new byte offset. No-op (returns offset unchanged) if the file is absent,
    so simulations and older engines degrade to the plain stdout log.
    """
    if run_dir is None:
        return offset
    path = run_dir / "events.jsonl"
    if not path.exists():
        return offset
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            chunk = f.read()
            new_offset = f.tell()
    except OSError:
        return offset

    for line in chunk.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = ev.get("kind")
        if kind == "agent_created":
            events.publish(assessment_id, {
                "type": "agent", "action": "created",
                "agent_id": ev.get("agent_id"), "name": ev.get("name"),
                "task": ev.get("task"), "parent_id": ev.get("parent_id"),
            })
        elif kind == "agent_status":
            events.publish(assessment_id, {
                "type": "agent", "action": "status",
                "agent_id": ev.get("agent_id"), "status": ev.get("status"),
            })
        elif kind == "chat_message":
            role = (ev.get("role") or "").lower()
            if role not in ("assistant", "user"):
                continue
            events.publish(assessment_id, {
                "type": "message", "role": role,
                "agent_id": ev.get("agent_id"), "content": ev.get("content", ""),
                "interrupted": bool(ev.get("interrupted")),
                "ts": ev.get("ts"),
            })
        elif kind == "tool_start":
            events.publish(assessment_id, {
                "type": "tool", "phase": "start",
                "agent_id": ev.get("agent_id"), "agent_name": ev.get("agent_name"),
                "tool_name": ev.get("tool_name"), "args": ev.get("args") or {},
                "ts": ev.get("ts"),
            })
        elif kind == "tool_end":
            events.publish(assessment_id, {
                "type": "tool", "phase": "end",
                "agent_id": ev.get("agent_id"), "tool_name": ev.get("tool_name"),
                "status": ev.get("status"), "ts": ev.get("ts"),
            })
    return new_offset


def _tail_file(path: Path | None, offset: int) -> tuple[list[str], int]:
    if path is None or not path.exists():
        return [], offset
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            new = f.read()
            return [ln for ln in new.splitlines() if ln.strip()], f.tell()
    except OSError:
        return [], offset


def _read_tail(path: Path | None, limit: int = 1500) -> str:
    if path is None or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:].strip()
    except OSError:
        return ""


def _final_status(run_dir: Path | None, returncode: int | None, cancelled: bool) -> tuple[str, str | None]:
    if cancelled:
        return AssessmentStatus.CANCELLED, None
    if run_dir is not None:
        rj = run_dir / "run.json"
        if rj.exists():
            try:
                data = json.loads(rj.read_text(encoding="utf-8", errors="replace"))
                st = str(data.get("status", "")).lower()
                if st in ("completed", "success", "finished"):
                    return AssessmentStatus.COMPLETED, None
                if st == "failed":
                    return AssessmentStatus.FAILED, "Strix reported the run as failed (see logs)."
            except (OSError, json.JSONDecodeError):
                pass
        # The engine writes the final report only when a run finishes and the
        # reporting agent completes. Its presence is a stronger success signal
        # than the CLI exit code, which can be non-zero even after a complete
        # assessment (late sandbox teardown, a subagent error post-reporting).
        if (run_dir / "penetration_test_report.md").exists():
            return AssessmentStatus.COMPLETED, None
    if returncode == 0:
        return AssessmentStatus.COMPLETED, None
    return AssessmentStatus.FAILED, f"Strix process exited with code {returncode}."


def _maybe_create_report(db, assessment_id: int, run_dir: Path | None) -> None:
    a = db.get(Assessment, assessment_id)
    if a is None or run_dir is None:
        return
    report_md = run_dir / "penetration_test_report.md"
    summary = ""
    if report_md.exists():
        try:
            summary = report_md.read_text(encoding="utf-8", errors="replace")[:1800]
        except OSError:
            summary = ""
    db.add(
        Report(
            title=f"{a.name} — Security Assessment Report",
            assessment_id=a.id,
            summary=summary or f"Assessment of {a.target} completed.",
            generated_by_id=a.created_by_id,
        )
    )
    db.commit()


def _run_real(assessment_id: int) -> None:
    db = SessionLocal()
    proc: subprocess.Popen | None = None
    run_dir: Path | None = None
    try:
        a = db.get(Assessment, assessment_id)
        if a is None:
            return

        repo = Path(settings.STRIX_REPO_PATH)
        runs_dir = repo / "strix_runs"
        before = {p.name for p in runs_dir.iterdir() if p.is_dir()} if runs_dir.exists() else set()
        mode = _SCAN_MODE_MAP.get(a.scan_type, "deep")

        cmd = shlex.split(settings.STRIX_LAUNCH_CMD) + [
            "--target", a.target, "--non-interactive", "--scan-mode", mode,
        ]
        if (a.instruction or "").strip():
            cmd += ["--instruction", a.instruction.strip()]

        env = os.environ.copy()
        if settings.STRIX_IMAGE:
            env["STRIX_IMAGE"] = settings.STRIX_IMAGE
        if settings.LLM_API_KEY:
            env.setdefault("LLM_API_KEY", settings.LLM_API_KEY)
        if settings.STRIX_LLM:
            env.setdefault("STRIX_LLM", settings.STRIX_LLM)

        # Stream the CLI's own stdout/stderr in real time. This is the reliable
        # live source: Strix's non-interactive Rich "Live" status stays silent on a
        # non-TTY pipe, but the startup panel, per-vulnerability panels, errors and
        # tracebacks all print here — and must reach the console promptly.
        logs_dir = repo / ".engine_logs"
        logs_dir.mkdir(exist_ok=True)
        capture_path = logs_dir / f"assessment-{assessment_id}.log"

        # child flushes each line instead of block-buffering
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        # Strix's non-interactive progress is a Rich "Live" panel that stays SILENT
        # on a non-TTY pipe. FORCE_COLOR makes Rich render frames anyway, so the
        # live console shows real progress (agents/tools/tokens/vulns). The reader
        # below collapses the redraw spam into just the lines that change.
        env["FORCE_COLOR"] = "1"
        env["COLUMNS"] = "200"
        env["LINES"] = "50"

        a.status = AssessmentStatus.RUNNING
        a.started_at = datetime.now(UTC)
        a.phase = "recon"
        a.progress = 3.0
        a.error = None
        db.commit()
        _emit_state(assessment_id, status=a.status, phase=a.phase, progress=a.progress)
        _log(db, assessment_id, "info", f"Launching Strix: {' '.join(cmd)} (cwd={repo})")

        try:
            proc = subprocess.Popen(  # nosec B603 - configured command, authorized scan
                cmd, cwd=str(repo), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
        except FileNotFoundError:
            _log(db, assessment_id, "error",
                 f"Could not launch '{settings.STRIX_LAUNCH_CMD}'. Set STRIX_LAUNCH_CMD "
                 f"(e.g. 'poetry run strix' or an absolute path). Falling back to simulation.")
            _simulate(assessment_id)
            return

        _processes[assessment_id] = proc

        # Reader thread: publish every CLI line live (snappy console) and queue it
        # for batched persistence. The monitor thread stays the *only* DB writer to
        # avoid SQLite lock contention.
        cli_q: queue.Queue[str] = queue.Queue()
        # Rolling window of recently-emitted lines. Rich repaints its panel several
        # times/sec; suppressing lines seen in the last ~80 collapses the repeated
        # frames so only genuinely new content (changed stats, findings, errors)
        # reaches the console.
        recent: deque[str] = deque(maxlen=80)

        def _is_frame(s: str) -> bool:
            # pure box-drawing / empty panel lines: "+----+", "|      |"
            inner = s.strip().strip("|").strip()
            return inner == "" or set(inner) <= set("+-=| ")

        def _pump_output() -> None:
            try:
                with capture_path.open("w", encoding="utf-8", errors="replace") as cf:
                    for raw in proc.stdout:  # type: ignore[union-attr]
                        line = _ANSI_RE.sub("", raw.rstrip("\r\n"))
                        if _is_frame(line):
                            continue
                        msg = line.strip().strip("|").strip()[:4000]
                        if not msg or msg in recent:
                            continue
                        recent.append(msg)
                        cf.write(msg + "\n")
                        cf.flush()
                        events.publish(assessment_id, {
                            "type": "log", "level": "info", "source": "engine", "message": msg,
                        })
                        cli_q.put(msg)
            except Exception:  # noqa: BLE001
                pass

        reader = threading.Thread(target=_pump_output, daemon=True)
        reader.start()

        def _persist_cli(limit: int = 1000) -> None:
            drained: list[str] = []
            while len(drained) < limit:
                try:
                    drained.append(cli_q.get_nowait())
                except queue.Empty:
                    break
            for ln in drained:
                db.add(LogEntry(level="info", source="engine", message=ln, assessment_id=assessment_id))
            if drained:
                db.commit()

        run_dir = _await_run_dir(runs_dir, before)
        if run_dir is not None:
            a = db.get(Assessment, assessment_id)
            a.strix_run_id = run_dir.name
            db.commit()
            _log(db, assessment_id, "info", f"Run directory: strix_runs/{run_dir.name}")
        else:
            _log(db, assessment_id, "warn",
                 "Run directory not created yet (sandbox warm-up); streaming engine output.")

        seen: set[str] = set()
        events_offset = 0
        start = time.time()
        expected = max(60, settings.STRIX_EXPECTED_DURATION)

        while proc.poll() is None:
            if assessment_id in _cancelled or _db_status(db, assessment_id) == AssessmentStatus.CANCELLED:
                cancel(assessment_id)
                break

            # The run dir often appears only after the sandbox is up — keep looking.
            if run_dir is None:
                run_dir = _await_run_dir(runs_dir, before, timeout=1)
                if run_dir is not None:
                    a = db.get(Assessment, assessment_id)
                    a.strix_run_id = run_dir.name
                    db.commit()
                    _log(db, assessment_id, "info", f"Run directory: strix_runs/{run_dir.name}")

            _ingest_findings(db, assessment_id, run_dir, seen)
            events_offset = _ingest_events(assessment_id, run_dir, events_offset)
            _persist_cli()

            # progress ramps toward 90% over the expected duration, nudged by findings
            elapsed = time.time() - start
            ramp = min(90.0, 5.0 + (elapsed / expected) * 80.0 + len(seen) * 2.0)
            a = db.get(Assessment, assessment_id)
            if a and a.status == AssessmentStatus.RUNNING:
                a.progress = round(max(a.progress, ramp), 1)
                a.phase = _phase_for_progress(a.progress)
                db.commit()
                _emit_state(assessment_id, status=a.status, phase=a.phase,
                            progress=a.progress, findings_count=len(seen))

            time.sleep(2)

        # final pass — let the reader drain the closed pipe, then flush everything.
        reader.join(timeout=10)
        _ingest_findings(db, assessment_id, run_dir, seen)
        events_offset = _ingest_events(assessment_id, run_dir, events_offset)
        _persist_cli(limit=10000)

        cancelled = assessment_id in _cancelled or _db_status(db, assessment_id) == AssessmentStatus.CANCELLED
        status, error = _final_status(run_dir, proc.returncode if proc else None, cancelled)

        # If it failed before producing a run dir, attach the CLI output tail so the
        # real reason (missing LLM creds, Docker down, etc.) is visible in the UI.
        if status == AssessmentStatus.FAILED:
            tail = _read_tail(capture_path)
            if tail:
                error = f"{error}\n\n--- engine output ---\n{tail}"

        a = db.get(Assessment, assessment_id)
        a.status = status
        a.finished_at = datetime.now(UTC)
        if status == AssessmentStatus.COMPLETED:
            a.progress = 100.0
            a.phase = "reporting"
        a.error = error
        db.commit()
        _emit_state(assessment_id, status=a.status, phase=a.phase, progress=a.progress,
                    findings_count=len(seen), error=a.error)
        _log(db, assessment_id, "info" if status == AssessmentStatus.COMPLETED else "error",
             f"Assessment {status} ({len(seen)} findings).")

        if status == AssessmentStatus.COMPLETED:
            _maybe_create_report(db, assessment_id, run_dir)

    except Exception as e:  # noqa: BLE001
        a = db.get(Assessment, assessment_id)
        if a is not None:
            a.status = AssessmentStatus.FAILED
            a.error = str(e)[:2000]
            a.finished_at = datetime.now(UTC)
            db.commit()
        _log(db, assessment_id, "error", f"Runner error: {e}")
    finally:
        _processes.pop(assessment_id, None)
        _cancelled.discard(assessment_id)
        db.close()


def _db_status(db, assessment_id: int) -> str | None:
    db.expire_all()
    a = db.get(Assessment, assessment_id)
    return a.status if a else None


# ── simulation fallback (engine not configured) ──────────────────────────────
def _simulate(assessment_id: int) -> None:
    db = SessionLocal()
    try:
        a = db.get(Assessment, assessment_id)
        if a is None:
            return
        a.status = AssessmentStatus.RUNNING
        a.started_at = datetime.now(UTC)
        a.phase = PHASES[0]
        db.commit()
        _log(db, assessment_id, "info", f"[simulation] Assessment started against {a.target}")

        for i, phase in enumerate(PHASES):
            if assessment_id in _cancelled or _db_status(db, assessment_id) == AssessmentStatus.CANCELLED:
                _log(db, assessment_id, "warn", "Assessment cancelled")
                a = db.get(Assessment, assessment_id)
                a.status = AssessmentStatus.CANCELLED
                db.commit()
                return
            a = db.get(Assessment, assessment_id)
            a.phase = phase
            a.progress = round((i / len(PHASES)) * 100, 1)
            db.commit()
            _emit_state(assessment_id, status=a.status, phase=a.phase, progress=a.progress)
            _log(db, assessment_id, "info", f"[simulation] Phase: {phase}")
            if phase == "post-exploitation":
                for kind, title, host, detail in [
                    (PostExKind.SESSION, "Meterpreter session opened (www-data)", a.target,
                     "php/meterpreter reverse shell established via Drupalgeddon2."),
                    (PostExKind.PRIVESC, "Privilege escalation to root", a.target,
                     "Kernel exploit / sudo misconfig escalated www-data -> root."),
                    (PostExKind.CREDENTIAL, "Harvested settings.php DB credentials", a.target,
                     "Extracted MySQL credentials from /var/www/settings.php."),
                    (PostExKind.EXFIL, "Dumped users table (1,204 records)", a.target,
                     "Exported the application users table as proof of impact."),
                ]:
                    _add_post_ex(db, assessment_id, kind=kind, title=title, host=host, detail=detail)
            time.sleep(2)

        a = db.get(Assessment, assessment_id)
        for title, sev, cve in [
            ("Drupalgeddon2 RCE via Forms API", Severity.CRITICAL, "CVE-2018-7600"),
            ("Missing security headers", Severity.MEDIUM, None),
            ("Verbose server banner", Severity.LOW, None),
        ]:
            db.add(Finding(
                assessment_id=assessment_id, title=title, severity=sev, cve=cve,
                description="Discovered during simulated assessment.",
                recommendation="Patch and restrict access.", evidence="See logs.",
            ))
            if a is not None:
                notify_service.notify_finding(a.name, a.target, title, str(sev), cve)
        a.status = AssessmentStatus.COMPLETED
        a.phase = "reporting"
        a.progress = 100.0
        a.finished_at = datetime.now(UTC)
        db.commit()
        _emit_state(assessment_id, status=a.status, phase=a.phase, progress=a.progress, findings_count=3)
        _log(db, assessment_id, "info", "[simulation] Assessment completed")
    except Exception as e:  # noqa: BLE001
        a = db.get(Assessment, assessment_id)
        if a is not None:
            a.status = AssessmentStatus.FAILED
            a.error = str(e)
            db.commit()
    finally:
        _cancelled.discard(assessment_id)
        db.close()
