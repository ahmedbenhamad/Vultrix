"""Live-console streaming: every line the engine prints must reach the logs.

Regression for the bug where the runner capped CLI output at 60 lines per poll
cycle *while advancing the read offset*, permanently dropping the rest — so the
live console stalled after the startup banner. Also covers the wrapper that
turns Rich Live-panel redraws into printed frames so the live-stats content
reaches the pipe (matching what interactive-mode TUI shows).
"""

import subprocess
import sys
import textwrap
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.log import LogEntry
from app.services import strix_service

API = "/api/v1"
N_LINES = 200

WRAPPER = Path(__file__).resolve().parents[1] / "strix_stream.py"


def test_engine_output_is_fully_streamed(client, admin_headers, tmp_path, monkeypatch):
    aid = client.post(
        f"{API}/assessments", headers=admin_headers,
        json={"name": "stream", "target": "e.com", "scan_type": "quick"},
    ).json()["id"]

    # A fake "engine" that floods stdout far past the old 60-line/cycle cap.
    script = tmp_path / "fake_strix.py"
    script.write_text(
        "import sys\n"
        f"for i in range({N_LINES}):\n"
        "    print(f'MARKER-{i:03d}')\n"
        "    sys.stdout.flush()\n",
        encoding="utf-8",
    )
    py = sys.executable.replace("\\", "/")
    monkeypatch.setattr(settings, "STRIX_REPO_PATH", str(tmp_path))
    monkeypatch.setattr(settings, "STRIX_LAUNCH_CMD", f'"{py}" "{script.as_posix()}"')
    # No real run directory is produced — don't wait the 90s warm-up window.
    monkeypatch.setattr(strix_service, "_await_run_dir", lambda *a, **k: None)

    strix_service._run_real(aid)  # blocks until the process ends + reader drains

    db = SessionLocal()
    try:
        msgs = [
            r.message
            for r in db.execute(
                select(LogEntry).where(LogEntry.assessment_id == aid)
            ).scalars().all()
        ]
    finally:
        db.close()

    markers = {m for m in msgs if m.startswith("MARKER-")}
    assert len(markers) == N_LINES, f"dropped {N_LINES - len(markers)} of {N_LINES} lines"
    # spot-check first and last so ordering/truncation regressions are caught too
    assert "MARKER-000" in markers
    assert f"MARKER-{N_LINES - 1:03d}" in markers


def test_wrapper_streams_rich_live_content(tmp_path):
    """The wrapper must turn ``rich.live.Live`` cursor-based redraws into printed
    frames so the live-stats panel content actually reaches a captured pipe.

    Without the wrapper Rich detects the non-TTY and Live emits nothing; the
    web console then stalls after the startup banner (bug the user reported).
    """
    # Isolate the wrapper's monkey-patch so it can be imported without pulling in
    # the real Strix CLI, then drive a small Rich `Live` scenario through a pipe.
    stub = tmp_path / "strix"
    stub_interface = stub / "interface"
    stub_interface.mkdir(parents=True)
    (stub / "__init__.py").write_text("", encoding="utf-8")
    (stub_interface / "__init__.py").write_text("", encoding="utf-8")
    (stub_interface / "main.py").write_text(
        textwrap.dedent(
            """
            import time
            from rich.console import Console
            from rich.live import Live
            from rich.panel import Panel

            def main():
                console = Console()
                # Startup banner (already streams — sanity check)
                console.print(Panel("STARTUP", title="STRIX"))
                # Rich Live panel that would normally be invisible over a pipe.
                with Live(Panel("stats=frame-0"), console=console, refresh_per_second=2) as live:
                    for i in range(1, 4):
                        time.sleep(2.2)   # exceed the wrapper's 2.0s throttle
                        live.update(Panel(f"stats=frame-{i}"))
                # A per-vulnerability panel (also already streams)
                console.print(Panel("FINDING", title="vuln-0001", border_style="red"))
                return 0
            """
        ),
        encoding="utf-8",
    )

    import os

    env = os.environ.copy()  # preserve APPDATA/user-site so Rich imports cleanly
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(WRAPPER)],
        capture_output=True, text=True, timeout=30, env=env,
    )
    out = proc.stdout

    # All three sources of interactive-mode content must appear in the pipe:
    assert "STARTUP" in out, "startup banner missing"
    assert "FINDING" in out, "per-vulnerability panel missing"
    # The Live-panel frames — the whole point of the wrapper — must stream too.
    # Frame-0 comes from __enter__; later frames come from the throttled updates.
    assert "stats=frame-0" in out, "Live initial frame missing"
    assert "stats=frame-3" in out, "Live update frames missing (Rich Live not patched)"
