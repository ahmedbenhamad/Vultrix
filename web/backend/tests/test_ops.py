"""Phase 5/6: scan instruction, webhook alert thresholds, readiness probes."""

from app.services import notify_service

API = "/api/v1"


def test_alert_threshold_default_high():
    # default ALERT_MIN_SEVERITY=high
    assert notify_service._meets_threshold("critical") is True
    assert notify_service._meets_threshold("high") is True
    assert notify_service._meets_threshold("medium") is False
    assert notify_service._meets_threshold("low") is False


def test_alert_payload_slack_vs_generic(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ALERT_WEBHOOK_URL", "https://hooks.slack.com/services/x")
    slack = notify_service._payload("Scan", "t.com", "SQLi", "critical", "CVE-1")
    assert set(slack.keys()) == {"text"} and "CRITICAL" in slack["text"]

    monkeypatch.setattr(settings, "ALERT_WEBHOOK_URL", "https://example.com/hook")
    generic = notify_service._payload("Scan", "t.com", "SQLi", "critical", "CVE-1")
    assert generic["event"] == "finding.discovered" and generic["severity"] == "critical"


def test_notify_finding_noop_without_webhook():
    # no webhook configured -> must not raise
    notify_service.notify_finding("Scan", "t.com", "x", "critical", None)


def test_scan_instruction_roundtrip(client, admin_headers):
    aid = client.post(
        f"{API}/assessments", headers=admin_headers,
        json={"name": "instr", "target": "e.com", "scan_type": "full",
              "instruction": "Focus on IDOR and auth bypass"},
    ).json()["id"]
    d = client.get(f"{API}/assessments/{aid}", headers=admin_headers).json()
    assert d["instruction"] == "Focus on IDOR and auth bypass"


def test_livez(client):
    assert client.get("/livez").json()["status"] == "alive"


def test_readyz_reports_db_ok(client):
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert "engine" in body["checks"]
