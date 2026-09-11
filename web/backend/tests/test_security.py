"""Phase 1 security tests: cookie auth + CSRF, object-level authz, MFA, lockout, audit chain."""

import pyotp

API = "/api/v1"


def _bearer_login(client, email: str, password: str, otp: str | None = None) -> dict:
    data = {"username": email, "password": password}
    if otp:
        data["otp"] = otp
    r = client.post(f"{API}/auth/login", data=data)
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    client.cookies.clear()  # drop cookies -> pure bearer (no CSRF gating) for the rest of the test
    return {"Authorization": f"Bearer {token}"}


def _make_user(client, admin_headers, email, role_name="analyst", password="TestPass123"):
    roles = client.get(f"{API}/roles", headers=admin_headers).json()
    rid = next(r["id"] for r in roles if r["name"] == role_name)
    client.post(
        f"{API}/users", headers=admin_headers,
        json={"email": email, "password": password, "role_id": rid},
    )
    return email, password


# ── cookie auth + CSRF ────────────────────────────────────────────────────────
def test_login_sets_httponly_cookies(client):
    r = client.post(f"{API}/auth/login", data={"username": "admin@strix.local", "password": "ChangeMe123!"})
    assert r.status_code == 200
    cookies = r.cookies
    assert "strix_access" in cookies and "strix_refresh" in cookies and "strix_csrf" in cookies
    client.cookies.clear()


def test_csrf_blocks_cookie_mutation_without_header(client):
    # authenticate via cookies (no bearer)
    client.post(f"{API}/auth/login", data={"username": "admin@strix.local", "password": "ChangeMe123!"})
    csrf = client.cookies.get("strix_csrf")

    # cookie-auth POST without the CSRF header -> blocked
    r = client.post(f"{API}/assessments", json={"name": "x", "target": "y"})
    assert r.status_code == 403

    # same POST WITH the CSRF header -> allowed
    r = client.post(
        f"{API}/assessments",
        json={"name": "csrf-ok", "target": "example.com"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 201, r.text
    client.cookies.clear()


def test_logout_clears_cookies(client):
    client.post(f"{API}/auth/login", data={"username": "admin@strix.local", "password": "ChangeMe123!"})
    csrf = client.cookies.get("strix_csrf")
    r = client.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    client.cookies.clear()


# ── object-level authz ────────────────────────────────────────────────────────
def test_analyst_sees_only_own_assessments(client, admin_headers):
    email, pw = _make_user(client, admin_headers, "analyst-authz@strix.io", "analyst")
    ah = _bearer_login(client, email, pw)

    # analyst creates one
    r = client.post(f"{API}/assessments", headers=ah, json={"name": "mine", "target": "a.example.com"})
    assert r.status_code == 201
    mine_id = r.json()["id"]

    # admin creates one owned by admin
    r = client.post(f"{API}/assessments", headers=admin_headers, json={"name": "admins", "target": "b.example.com"})
    admin_aid = r.json()["id"]

    # analyst list -> only own
    listed = client.get(f"{API}/assessments", headers=ah).json()["items"]
    ids = {a["id"] for a in listed}
    assert mine_id in ids and admin_aid not in ids

    # analyst cannot fetch the admin's assessment (404, no enumeration)
    assert client.get(f"{API}/assessments/{admin_aid}", headers=ah).status_code == 404

    # admin (read:all) can see the analyst's
    assert client.get(f"{API}/assessments/{mine_id}", headers=admin_headers).status_code == 200


# ── account lockout ───────────────────────────────────────────────────────────
def test_account_lockout_after_failures(client, admin_headers):
    email, pw = _make_user(client, admin_headers, "lockme@strix.io", "viewer")
    for _ in range(5):  # MAX_FAILED_LOGINS
        client.post(f"{API}/auth/login", data={"username": email, "password": "wrong"})
    # even the CORRECT password is now rejected with 403 (locked)
    r = client.post(f"{API}/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 403
    assert "lock" in r.json()["detail"].lower()
    client.cookies.clear()


# ── TOTP MFA ──────────────────────────────────────────────────────────────────
def test_mfa_setup_enable_and_login(client, admin_headers):
    email, pw = _make_user(client, admin_headers, "mfa-user@strix.io", "analyst")
    ah = _bearer_login(client, email, pw)

    setup = client.post(f"{API}/auth/mfa/setup", headers=ah).json()
    assert setup["secret"] and len(setup["recovery_codes"]) == 10
    totp = pyotp.TOTP(setup["secret"])

    r = client.post(f"{API}/auth/mfa/enable", headers=ah, json={"code": totp.now()})
    assert r.status_code == 200, r.text
    client.cookies.clear()

    # login without OTP -> 401 MFA_REQUIRED
    r = client.post(f"{API}/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 401 and r.json()["detail"] == "MFA_REQUIRED"

    # login with a valid OTP -> success
    r = client.post(f"{API}/auth/login", data={"username": email, "password": pw, "otp": totp.now()})
    assert r.status_code == 200
    client.cookies.clear()


# ── tamper-evident audit ──────────────────────────────────────────────────────
def test_audit_chain_intact(client, admin_headers):
    r = client.get(f"{API}/audit/verify", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["intact"] is True
