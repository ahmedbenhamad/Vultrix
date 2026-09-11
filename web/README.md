# Strix Console — Web Interface

A professional, secure web console for the Strix AI penetration-testing platform:
statistics, assessments pipeline & tracking, findings, reports (PDF/CSV/JSON export),
logs, an AI assistant, plus full user / role / permission management and an audit trail.

```
web/
├── backend/     FastAPI + SQLAlchemy + PostgreSQL   (auth, RBAC, API)
├── frontend/    Next.js (App Router) + Tailwind      (dashboard UI)
└── docker-compose.yml   db + backend + frontend
```

## Features

| Area | What's included |
|------|-----------------|
| **Auth** | JWT access + refresh, Argon2 password hashing, transparent rehash, refresh-token rotation |
| **RBAC** | `resource:action` permissions, roles (admin/manager/analyst/viewer + custom), per-endpoint guards |
| **Dashboard** | Live stat cards, 14-day activity area chart, severity donut (Recharts) |
| **Assessments** | Create → run → live pipeline tracking (recon → vuln → exploitation → reporting), cancel, delete |
| **Findings** | Severity-tagged, CVE-linked, per-assessment |
| **Reports** | Export to PDF (reportlab), CSV, JSON |
| **Logs** | Filterable execution/system logs |
| **Audit trail** | Immutable record of every security-relevant action (actor, IP, result) |
| **AI Assistant** | Chat UI with sessions; RAG-grounded, LLM-pluggable |
| **Users & Roles** | Full CRUD, role assignment, permission catalog with a checkbox editor |
| **Security** | CORS allow-list, self-guarding (can't disable/delete own account), system-role locks, 0 npm vulnerabilities |

## Quick start (two terminals, local, zero infra)

**Backend** (SQLite, self-seeds admin + demo data):
```bash
cd web/backend
python -m venv .venv && .venv/Scripts/activate     # source .venv/bin/activate on *nix
pip install -r requirements.txt
cp .env.example .env
# in .env set:  DATABASE_URL=sqlite+pysqlite:///./strix_console.db
uvicorn app.main:app --reload --port 8000
```

**Frontend**:
```bash
cd web/frontend
npm install
npm run dev            # http://localhost:3000  (proxies /api/* -> :8000)
```

Log in with the seeded admin: **admin@strix.local / ChangeMe123!**

## Full stack with Postgres (Docker)
```bash
cd web
SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(64))") \
docker compose up --build
# UI: http://localhost:3000   API docs: http://localhost:8000/api/v1/docs
```

## Architecture notes
- The browser stays same-origin: Next.js `rewrites` proxy `/api/*` to the FastAPI backend.
- Every mutating endpoint is permission-guarded server-side; the frontend also hides
  nav/actions the user lacks permission for (defense in depth, not the only gate).
- The assessment engine is currently **simulated** in `backend/app/services/strix_service.py`
  (a background thread walking the real pipeline phases). Swap `_simulate` for a subprocess/API
  call into the Strix CLI to go live — the DB contract (status/phase/progress/findings/logs) is
  unchanged, so the UI keeps working.
- The AI assistant (`backend/app/services/assistant_service.py`) returns grounded canned
  replies until you set `LLM_API_KEY`; RAG grounding activates when `RAG_BASE_URL` is reachable.

## Verified
- Backend: login, `/me`, RBAC (viewer → 403 on admin actions), stats, create/run pipeline,
  PDF+CSV export — all tested green on Python 3.14.
- Frontend: production build compiles all 14 routes, **0 npm vulnerabilities**, dashboard +
  assessments render live data end-to-end through the proxy.

## Security hardening TODO before production
- [ ] Set a strong `SECRET_KEY` and rotate; never ship the dev default.
- [ ] Put the API behind TLS; set `ENVIRONMENT=production`.
- [ ] Add rate limiting on `/auth/login` (e.g. slowapi) and account lockout.
- [ ] Tighten CORS to the real frontend origin only.
- [ ] Move JWTs to httpOnly cookies if you need XSS-hardening beyond localStorage.
