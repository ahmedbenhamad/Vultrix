# Strix Console — Docker deployment

Package the console (FastAPI backend + Next.js frontend) as two Docker Hub
images and launch the full stack (with Postgres + Redis) in one command.

## Images

| Service  | Image                                       |
|----------|---------------------------------------------|
| Backend  | `ahmedbenhamad/strix-console-backend`       |
| Frontend | `ahmedbenhamad/strix-console-frontend`      |

Postgres (`postgres:16-alpine`) and Redis (`redis:7-alpine`) are pulled from the
official images — nothing to build for those.

## Build & push (maintainer)

Requires the Docker daemon running and a `docker login` you perform yourself.

```powershell
# from web/
docker login                       # enter YOUR Docker Hub credentials
./build-and-push.ps1               # -Namespace ahmedbenhamad -Tag 0.1.0
# bash equivalent: ./build-and-push.sh
```

The script builds both images, tags them `:0.1.0` and `:latest`, and pushes them.
Use `-SkipPush` (PowerShell) or `SKIP_PUSH=1` (bash) to build without publishing.

## Launch (anyone)

```bash
# from web/
cp .env.example .env               # then edit secrets
docker compose -f docker-compose.hub.yml up -d
```

- Frontend: <http://localhost:3000>
- Backend API docs: <http://localhost:8080/api/v1/docs>
- First login: the `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` from `.env`
  (default `admin@strix.local` / `ChangeMe123!`). Schema and admin are seeded
  automatically on first backend startup.

Stop / reset:

```bash
docker compose -f docker-compose.hub.yml down          # stop
docker compose -f docker-compose.hub.yml down -v       # stop + wipe the DB volume
```

## Configuration

All settings live in `.env` (see `.env.example`). Key ones:

| Variable                 | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `SECRET_KEY`             | JWT/cookie signing secret — **change for production**|
| `FIRST_ADMIN_*`          | Seeded admin account                                 |
| `POSTGRES_*`             | Database name / credentials                          |
| `FRONTEND_PORT` / `BACKEND_PORT` | Host port mappings                           |
| `STRIX_FORCE_SIMULATION` | `true` runs the built-in engine simulation (default) |
| `RAG_BASE_URL` / `LLM_API_KEY` | Optional AI-assistant / RAG wiring             |

> The console runs fully standalone in simulation mode. Wiring the real Strix
> engine (which drives a Kali Docker sandbox) is out of scope for this image set.

## Local development (build from source)

`docker-compose.yml` (build-based) still works for iterating locally:

```bash
docker compose up --build
```
