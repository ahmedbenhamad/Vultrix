"""Output screen: /output endpoint + agent-tree / telemetry parsers."""

import json

from app.services import output_service

API = "/api/v1"


def test_output_endpoint_for_simulation(client, admin_headers):
    aid = client.post(
        f"{API}/assessments", headers=admin_headers,
        json={"name": "out", "target": "e.com", "scan_type": "quick"},
    ).json()["id"]
    r = client.get(f"{API}/assessments/{aid}/output", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["has_run_dir"] is False
    assert body["agents"] == []


def test_parse_agents_builds_tree(tmp_path):
    state = tmp_path / ".state"
    state.mkdir()
    (state / "agents.json").write_text(json.dumps({
        "statuses": {"root": "running", "child": "completed"},
        "parent_of": {"root": None, "child": "root"},
        "names": {"root": "strix", "child": "XSS Agent"},
        "metadata": {"root": {"task": "full pentest"}, "child": {"task": "test xss"}},
        "pending_counts": {"root": 1, "child": 0},
    }), encoding="utf-8")

    nodes = output_service.parse_agents(tmp_path)
    assert len(nodes) == 2
    root = next(n for n in nodes if n["name"] == "strix")
    child = next(n for n in nodes if n["name"] == "XSS Agent")
    assert root["parent"] is None and root["status"] == "running" and root["pending"] == 1
    assert child["parent"] == "root" and child["task"] == "test xss"


def test_parse_telemetry(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({
        "status": "completed",
        "start_time": "2026-07-09T00:00:00+00:00",
        "llm_usage": {"requests": 6, "input_tokens": 100, "output_tokens": 20, "total_tokens": 120, "cost": 0.0123},
    }), encoding="utf-8")
    t = output_service.parse_telemetry(tmp_path)
    assert t["requests"] == 6 and t["total_tokens"] == 120 and t["cost"] == 0.0123
