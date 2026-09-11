"""End-to-end smoke tests over the async stack (auth, RBAC, CRUD, stats, audit)."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_me(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "admin@vultrix.local"
    assert body["role"]["name"] == "admin"
    assert len(body["permissions"]) > 0


def test_login_rejects_bad_password(client):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vultrix.local", "password": "wrong"},
    )
    assert r.status_code == 401


def test_stats_dashboard(client, admin_headers):
    r = client.get("/api/v1/stats/dashboard", headers=admin_headers)
    assert r.status_code == 200
    assert "severity_breakdown" in r.json()


def test_roles_seeded(client, admin_headers):
    r = client.get("/api/v1/roles", headers=admin_headers)
    assert r.status_code == 200
    names = {role["name"] for role in r.json()}
    assert {"admin", "manager", "analyst", "viewer"} <= names


def test_assessment_create_and_list(client, admin_headers):
    r = client.post(
        "/api/v1/assessments",
        headers=admin_headers,
        json={"name": "Test scan", "target": "example.com", "scan_type": "quick"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    r = client.get(f"/api/v1/assessments/{aid}", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["target"] == "example.com"


def test_rbac_viewer_is_blocked(client, admin_headers):
    roles = client.get("/api/v1/roles", headers=admin_headers).json()
    viewer_id = next(r["id"] for r in roles if r["name"] == "viewer")
    client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"email": "rbac-viewer@vultrix.io", "password": "ViewerPass1", "role_id": viewer_id},
    )
    tok = client.post(
        "/api/v1/auth/login",
        data={"username": "rbac-viewer@vultrix.io", "password": "ViewerPass1"},
    ).json()["access_token"]
    vh = {"Authorization": f"Bearer {tok}"}

    assert client.get("/api/v1/assessments", headers=vh).status_code == 200  # allowed
    assert client.get("/api/v1/users", headers=vh).status_code == 403  # denied


def test_audit_trail_records_actions(client, admin_headers):
    r = client.get("/api/v1/audit", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total"] > 0  # logins + user creates above were recorded
