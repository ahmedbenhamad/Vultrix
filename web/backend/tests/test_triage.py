"""Phase 5: findings triage workflow + scan diffing."""

from app.api.routes.assessments import _finding_key

API = "/api/v1"


def test_finding_key_prefers_cve():
    assert _finding_key("Some Title", "CVE-2021-1") == "cve-2021-1"
    assert _finding_key("Some   Title", None) == "some title"


def _first_finding(client, admin_headers):
    items = client.get(f"{API}/assessments?status=completed", headers=admin_headers).json()["items"]
    for it in items:
        d = client.get(f"{API}/assessments/{it['id']}", headers=admin_headers).json()
        if d["findings"]:
            return it["id"], d["findings"][0]["id"]
    raise AssertionError("no seeded finding to triage")


def test_triage_finding_updates_status_and_severity(client, admin_headers):
    aid, fid = _first_finding(client, admin_headers)
    r = client.patch(
        f"{API}/assessments/{aid}/findings/{fid}",
        headers=admin_headers,
        json={"status": "confirmed", "severity_override": "critical", "triage_notes": "verified manually"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "confirmed"
    assert body["effective_severity"] == "critical"
    assert body["triage_notes"] == "verified manually"


def test_triage_rejects_bad_status(client, admin_headers):
    aid, fid = _first_finding(client, admin_headers)
    r = client.patch(f"{API}/assessments/{aid}/findings/{fid}", headers=admin_headers, json={"status": "bogus"})
    assert r.status_code == 400


def test_scan_diff(client, admin_headers):
    from app.core.database import SessionLocal
    from app.models.assessment import Assessment, AssessmentStatus, Finding

    db = SessionLocal()
    try:
        base = Assessment(name="Baseline", target="diff.example.com", status=AssessmentStatus.COMPLETED)
        db.add(base)
        db.flush()
        db.add(Finding(assessment_id=base.id, title="Old vuln", severity="high", cve="CVE-0001"))
        db.add(Finding(assessment_id=base.id, title="Shared vuln", severity="medium", cve="CVE-0002"))

        cur = Assessment(name="Current", target="diff.example.com", status=AssessmentStatus.COMPLETED)
        db.add(cur)
        db.flush()
        db.add(Finding(assessment_id=cur.id, title="Shared vuln", severity="medium", cve="CVE-0002"))
        db.add(Finding(assessment_id=cur.id, title="New vuln", severity="critical", cve="CVE-0003"))
        db.commit()
        cur_id, base_id = cur.id, base.id
    finally:
        db.close()

    d = client.get(f"{API}/assessments/{cur_id}/diff", headers=admin_headers).json()
    assert d["baseline_id"] == base_id
    assert {f["title"] for f in d["new"]} == {"New vuln"}
    assert {f["title"] for f in d["fixed"]} == {"Old vuln"}
    assert {f["title"] for f in d["unchanged"]} == {"Shared vuln"}
