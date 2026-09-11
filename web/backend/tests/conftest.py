"""Test configuration.

Point the app at an isolated temp SQLite DB *before* any app module imports so the
sync/async engines bind to it. Environment variables take precedence over .env in
pydantic-settings, so this reliably overrides the dev database.
"""

import os
import pathlib
import tempfile

_TEST_DB = pathlib.Path(tempfile.gettempdir()) / "strix_console_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@strix.local"
os.environ["FIRST_ADMIN_PASSWORD"] = "ChangeMe123!"
os.environ["STRIX_FORCE_SIMULATION"] = "true"  # never launch the real engine in tests
os.environ["LOGIN_RATELIMIT"] = "1000/minute"  # don't let the suite's many logins trip the limiter

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    # `with TestClient(...)` runs the lifespan -> schema + seed.
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_cookies(client):
    # Tests authenticate via bearer header; clear any cookies a prior login set so
    # the CSRF middleware (cookie-auth only) doesn't gate bearer-based mutations.
    client.cookies.clear()
    yield


@pytest.fixture(scope="session")
def admin_token(client) -> str:
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@strix.local", "password": "ChangeMe123!"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
