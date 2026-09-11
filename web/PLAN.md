# Strix Console — Enhancement Roadmap

Locked decisions (2026-07-07):
- **Data layer:** PostgreSQL + **async SQLAlchemy** (asyncpg), Alembic migrations.
- **Auth:** httpOnly + SameSite **cookies** + CSRF + **TOTP MFA** (replaces localStorage/JWT-in-JS).
- **Sequencing:** strict Phase 0 → 6 (foundations-first, bottom-up).
- **Task queue:** RQ + Redis (both already vendored in the 0.7.0 wheels).

Two explicitly-requested features land in **Phase 3** (Strix Output visualization screen)
and **Phase 4** (Post-exploitation phase).

Status legend: ⬜ todo · 🔄 in progress · ✅ done

---

## Phase 0 — Foundations  🔄 (core done)
Goal: async Postgres data layer, migrations, durable job queue, test/CI harness.
- ✅ Add deps: `asyncpg`, `aiosqlite`, `greenlet`, `redis`, `rq`, `pyotp`, `slowapi`, `pytest`
- ✅ Convert `core/database.py` → async engine + `async_sessionmaker` + async `get_db`
      (dual: async for web, sync engine for worker/seed/alembic; driver derived per URL)
- ✅ Convert all routes/services to `async def` + `AsyncSession` (verified live + tests)
- ✅ Alembic init + baseline migration (applies clean on fresh DB; seed still create_all for dev)
- ✅ docker-compose: Postgres + Redis services with healthchecks
- ✅ Test harness: pytest (8 smoke tests, green) + orphan-run reconciler on startup
- ✅ CI workflow (`.github/workflows/web-ci.yml`) + ruff config (lint clean)
- ⬜ RQ worker extraction (scans still run in a daemon thread; reconciler covers restarts) — deferred
- ⬜ Vitest/RTL + Playwright e2e frontend tests — deferred

## Phase 1 — Auth & security hardening  ✅ DONE (2026-07-08)
- ✅ Cookie auth (httpOnly/SameSite) + CSRF double-submit; `api.ts` + `auth.tsx` reworked
      (backend accepts cookie OR bearer; access token no longer readable by JS — verified)
- ✅ Server-side `user_sessions` table; refresh rotation + reuse detection; per-session +
      "sign out everywhere" revoke (UI in Settings)
- ✅ Login rate-limit (slowapi) + account lockout (5 fails → 15 min)
- ✅ TOTP MFA (pyotp) + 10 recovery codes; mandatory for admin/manager roles; setup UI in Settings
- ✅ Security-headers middleware (CSP, HSTS in prod, X-Frame-Options, X-Content-Type-Options)
- ✅ Object-level authz (`assessment:read:all` vs own-rows); list filter + 404 on non-owned
- ✅ Tamper-evident hash-chained audit trail + `/audit/verify` endpoint
- ✅ Alembic migration `280fb2b1117f`; 7 new security tests (15 total green); ruff clean

## Phase 2 — Reliability & live-data backbone  ✅ DONE (2026-07-09)
- ✅ WebSocket hub `/ws/assessments/{id}` — snapshot + live state/log events; cookie or
      `?token=` auth + ownership check. In-process event bus (`core/events.py`) bridges the
      threaded runner → loop → WS (swap for Redis when RQ lands). Works through the Next proxy.
- ✅ Orphaned-run reconciler on startup (Phase 0) — marks stuck-RUNNING failed
- ✅ Concurrency cap (`STRIX_MAX_CONCURRENT`, bounded semaphore; extras stay QUEUED)
- ✅ Frontend: `useLiveAssessment` hook + live overlay + streaming console on the detail page
      (browser-verified: console streamed 7→14 lines live, status→completed via WS)
- ✅ 3 WS tests (18 total green), ruff clean
- ⬜ Full RQ worker extraction (still a daemon thread) — deferred; needs Redis to test

## Phase 3 — ⭐ Strix Output Visualization screen  ✅ DONE (2026-07-09)
- ✅ Route `/assessments/[id]/output` + "Engine output" button on the detail page
- ✅ Agent tree from `.state/agents.json` — collapsible, per-agent status dot + task
      (`output_service.parse_agents` builds the tree via `parent_of`)
- ✅ Live terminal — `strix.log`/CLI stream over the Phase-2 WS, with search + level
      filter + autoscroll; ANSI escape codes stripped at ingestion
- ✅ Run telemetry — requests / in·out·total tokens / cost / elapsed from `run.json.llm_usage`
- ✅ Backend `GET /assessments/{id}/output` (ownership-checked) + 3 parser/endpoint tests
- ✅ Browser-verified against a REAL run dir (6 requests, 68,542 tokens, agent "strix", live console)
- ⬜ (opt) proxy-traffic panel + tool timeline — deferred

## Phase 4 — ⭐ Post-exploitation phase  ✅ DONE (2026-07-09)
- ✅ Pipeline → recon → vuln-assessment → exploitation → **post-exploitation** → reporting
- ✅ Backend: `PHASES` + `_phase_for_progress` (5 bands) + simulation emits post-ex events
- ✅ `post_ex_events` table (kind: session|privesc|persistence|lateral|exfil|credential, title, detail, host, evidence)
- ✅ Real-run parse from finding `## Post-Exploitation` sections (`_parse_finding_md` + `_add_post_ex`)
- ✅ Frontend: 5th stepper node + Post-exploitation timeline section (typed icons, host, detail) on the detail page
- ✅ Migration `1fcd9c72d20f`; 4 new tests (25 total green); browser-verified with typed events

## Phase 5 — Domain features  🔄 (core done 2026-07-10)
- ✅ Findings triage workflow — status (open/confirmed/false_positive/remediated/accepted_risk),
      severity_override (effective_severity), assignee_id, triage_notes; `PATCH
      /assessments/{aid}/findings/{fid}` (perm `finding:triage`, analyst+); inline UI on detail page
- ✅ Scan diffing — `GET /assessments/{aid}/diff` compares vs previous completed scan of same target
      (new/fixed/unchanged, keyed by CVE|title); "Change since last scan" UI section
- ✅ Migration `80086a568ed3`; 4 new tests (29 total green); browser-verified (triage via cookie+CSRF, diff)
- ✅ Richer scan config: `--instruction` (Assessment.instruction → CLI flag + create-dialog textarea)
- ✅ Integrations: **webhook/Slack alerts** on findings ≥ ALERT_MIN_SEVERITY (`notify_service`)
- ✅ **Scheduling** — `schedules` table + APScheduler cron runner (`scheduler_service`), CRUD +
      `schedule:read`/`schedule:manage` perms, next-run via croniter, Schedules page + nav
- ⬜ Evidence attachments (req/resp, PoC, screenshots) — deferred
- ⬜ Multi-target scans, cost surfacing — deferred
- ⬜ Jira/GitHub issue creation, SIEM export — deferred
- ⬜ CVSS + CWE + OWASP/PCI mapping; report templating — deferred

## Phase 6 — Frontend quality + observability  🔄 (started 2026-07-10)
- ✅ **⌘K command palette** (`components/command-palette.tsx`) — permission-filtered nav + actions, mounted in app layout
- ✅ **Observability**: request-ID logging middleware (`X-Request-ID`) + `/readyz` (DB + engine) + `/livez`
- ✅ Alembic **naming convention** + squashed baseline `02a8ca478805` (fixes SQLite batch migrations)
- ⬜ TanStack Query; OpenAPI-generated TS client; server-side pagination/sort — deferred
- ⬜ react-hook-form + zod; a11y (focus traps/ARIA); error boundaries — deferred
- ⬜ OpenTelemetry; Prometheus — deferred
- ⬜ Hardened non-root containers; TLS via reverse proxy; DB backups; RQ worker — deferred

---

## Dependency graph
```
Phase 0 ──┬─> Phase 1 (auth)
          ├─> Phase 2 (live data) ──> Phase 3 (Output screen)
          ├─> Phase 4 (post-ex)
          └─> Phase 5 / 6
```
Phase 3 requires Phase 2. Phase 4 needs only Phase-0 migrations.
