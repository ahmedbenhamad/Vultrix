# Strix Console — Backend (FastAPI)

REST API for the Strix security-testing web interface: auth, RBAC, assessments,
logs, reports, exports, audit trail, and the AI-assistant proxy.

## Stack
FastAPI · SQLAlchemy 2 · Pydantic v2 · PostgreSQL · JWT (access+refresh) · Argon2

## Quick start (local, SQLite)

```bash
cd web/backend
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate on *nix
pip install -r requirements.txt
cp .env.example .env              # then edit SECRET_KEY etc.
# For zero-setup dev, set in .env:  DATABASE_URL=sqlite+pysqlite:///./strix_console.db
uvicorn app.main:app --reload --port 8000
```

The app seeds itself on first boot: default roles + permissions and the first
admin from `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD`.

- API docs:   http://localhost:8000/api/v1/docs
- Health:     http://localhost:8000/health

## Postgres / full stack

```bash
cd web
docker compose up --build       # db + backend + frontend
```

## RBAC model
- **Permissions** — `resource:action` strings (see `app/core/permissions.py`).
- **Roles** — named permission sets. System roles: `admin`, `manager`, `analyst`, `viewer`.
- **Users** — one role each; superusers implicitly hold every permission.
- Every mutating endpoint is guarded by `require_permission(...)`; security-relevant
  actions are written to the immutable **audit trail** (`/api/v1/audit`).

## The Strix engine (WIRED)
`app/services/strix_service.py` launches the **real** Strix engine and mirrors its
output into the DB live. To enable it, set in `.env`:

```
STRIX_REPO_PATH=/path/to/strix            # your Strix checkout (also where strix_runs/ is written)
STRIX_LAUNCH_CMD=strix                     # or "poetry run strix" / absolute path
STRIX_IMAGE=strix-sandbox:0.7.2            # sandbox image
STRIX_FORCE_SIMULATION=false               # true = always use the built-in simulation
```

On **Run**, the service executes:
```
<STRIX_LAUNCH_CMD> --target <target> --non-interactive --scan-mode <quick|standard|deep>
```
with `cwd = STRIX_REPO_PATH`, then watches the run directory Strix creates under
`strix_runs/<name>` and streams results into the DB:

| Strix artifact | Mirrored to |
|----------------|-------------|
| `vulnerabilities.csv` + `vulnerabilities/<id>.md` | `Finding` rows (title, severity, CVE, description, remediation) — idempotent |
| `strix.log` | `LogEntry` rows |
| `run.json` `status` | authoritative final status (completed/failed) |
| `penetration_test_report.md` | `Report` row summary |

Scan-type → mode: `quick→quick`, `api/infra→standard`, `full→deep`.
`/assessments/{id}/cancel` terminates the underlying process.

**Graceful fallback:** if `STRIX_REPO_PATH` is unset, or the launch binary isn't
found, or `STRIX_FORCE_SIMULATION=true`, it falls back to a built-in simulation so
the UI still works. Requires Docker + a reachable `strix` on PATH + LLM creds for
real runs (same prerequisites as running Strix from the CLI).

## Connecting the AI assistant
Set `LLM_API_KEY` (+ `ASSISTANT_LLM`) in `.env` and complete the TODO in
`app/services/assistant_service.py` to call LiteLLM. RAG grounding activates
automatically when `RAG_BASE_URL` is reachable.
