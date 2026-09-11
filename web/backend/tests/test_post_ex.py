"""Phase 4: post-exploitation phase + events."""

from app.services import strix_service

API = "/api/v1"


def test_pipeline_has_five_phases():
    assert strix_service.PHASES == [
        "recon", "vuln-assessment", "exploitation", "post-exploitation", "reporting",
    ]


def test_phase_for_progress_includes_post_ex():
    assert strix_service._phase_for_progress(80) == "post-exploitation"
    assert strix_service._phase_for_progress(95) == "reporting"


def test_new_assessment_exposes_empty_post_ex(client, admin_headers):
    aid = client.post(
        f"{API}/assessments", headers=admin_headers,
        json={"name": "pe", "target": "e.com", "scan_type": "quick"},
    ).json()["id"]
    d = client.get(f"{API}/assessments/{aid}", headers=admin_headers).json()
    assert "post_ex" in d and d["post_ex"] == []


def test_completed_assessments_have_post_ex(client, admin_headers):
    items = client.get(f"{API}/assessments?status=completed", headers=admin_headers).json()["items"]
    valid_kinds = {"session", "privesc", "persistence", "lateral", "exfil", "credential"}
    for it in items:
        d = client.get(f"{API}/assessments/{it['id']}", headers=admin_headers).json()
        if d["post_ex"]:
            assert {e["kind"] for e in d["post_ex"]} <= valid_kinds
            return
    raise AssertionError("expected a seeded completed assessment to have post-ex events")
