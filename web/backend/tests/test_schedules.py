"""Phase 5: recurring scan schedules (cron)."""

from app.services import scheduler_service

API = "/api/v1"


def test_validate_and_next_run():
    assert scheduler_service.validate_cron("0 2 * * *") is True
    assert scheduler_service.validate_cron("not a cron") is False
    assert scheduler_service.next_run("*/5 * * * *") is not None
    assert scheduler_service.next_run("bogus") is None


def test_schedule_crud(client, admin_headers):
    # create
    r = client.post(
        f"{API}/schedules", headers=admin_headers,
        json={"name": "Nightly", "target": "app.example.com", "scan_type": "full", "cron": "0 2 * * *"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    sid = body["id"]
    assert body["cron"] == "0 2 * * *"
    assert body["next_run_at"] is not None  # computed for enabled schedule

    # list
    listed = client.get(f"{API}/schedules", headers=admin_headers).json()
    assert any(s["id"] == sid for s in listed)

    # disable -> next_run_at cleared
    r = client.patch(f"{API}/schedules/{sid}", headers=admin_headers, json={"enabled": False})
    assert r.status_code == 200 and r.json()["enabled"] is False
    assert r.json()["next_run_at"] is None

    # delete
    assert client.delete(f"{API}/schedules/{sid}", headers=admin_headers).status_code == 200
    assert all(s["id"] != sid for s in client.get(f"{API}/schedules", headers=admin_headers).json())


def test_create_rejects_bad_cron(client, admin_headers):
    r = client.post(
        f"{API}/schedules", headers=admin_headers,
        json={"name": "x", "target": "y", "cron": "every tuesday"},
    )
    assert r.status_code == 400


def test_viewer_cannot_manage_schedules(client, admin_headers):
    roles = client.get(f"{API}/roles", headers=admin_headers).json()
    vid = next(r["id"] for r in roles if r["name"] == "viewer")
    client.post(f"{API}/users", headers=admin_headers,
                json={"email": "sched-viewer@vultrix.io", "password": "ViewerPass1", "role_id": vid})
    tok = client.post(f"{API}/auth/login",
                      data={"username": "sched-viewer@vultrix.io", "password": "ViewerPass1"}).json()["access_token"]
    vh = {"Authorization": f"Bearer {tok}"}
    r = client.post(f"{API}/schedules", headers=vh, json={"name": "x", "target": "y", "cron": "0 2 * * *"})
    assert r.status_code == 403
