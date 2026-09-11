"""Parse a Strix run directory's ``.state/agents.json`` (agent tree) and
``run.json`` (LLM token/cost telemetry) for the Output visualization screen.
"""

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.assessment import Assessment


def _run_dir(assessment: Assessment) -> Path | None:
    if not assessment.strix_run_id or not settings.STRIX_REPO_PATH:
        return None
    d = Path(settings.STRIX_REPO_PATH) / "strix_runs" / assessment.strix_run_id
    return d if d.exists() else None


def parse_agents(run_dir: Path) -> list[dict[str, Any]]:
    """Flat list of agent nodes (id, name, status, parent, task, pending)."""
    path = run_dir / ".state" / "agents.json"
    if not path.exists():
        return []
    try:
        d = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return []

    statuses = d.get("statuses", {}) or {}
    parents = d.get("parent_of", {}) or {}
    names = d.get("names", {}) or {}
    metadata = d.get("metadata", {}) or {}
    pending = d.get("pending_counts", {}) or {}

    nodes = []
    for aid in statuses:
        meta = metadata.get(aid) or {}
        task = meta.get("task", "") if isinstance(meta, dict) else ""
        nodes.append({
            "id": aid,
            "name": names.get(aid) or aid,
            "status": statuses.get(aid, "unknown"),
            "parent": parents.get(aid),
            "task": (task or "").strip()[:600],
            "pending": pending.get(aid, 0),
        })
    return nodes


def parse_telemetry(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / "run.json"
    if not path.exists():
        return None
    try:
        d = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None
    usage = d.get("llm_usage", {}) or {}
    return {
        "status": d.get("status"),
        "start_time": d.get("start_time"),
        "end_time": d.get("end_time"),
        "requests": usage.get("requests", 0),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "cost": usage.get("cost", 0),
    }


def read_output(assessment: Assessment) -> dict[str, Any]:
    run_dir = _run_dir(assessment)
    if run_dir is None:
        return {"run_id": assessment.strix_run_id, "has_run_dir": False, "agents": [], "telemetry": None}
    return {
        "run_id": run_dir.name,
        "has_run_dir": True,
        "agents": parse_agents(run_dir),
        "telemetry": parse_telemetry(run_dir),
    }
