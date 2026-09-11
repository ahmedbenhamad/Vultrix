# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Strix Console — Backend (FastAPI / uvicorn)
# Schema + first-admin seeding run automatically on startup (idempotent).
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg[binary]/asyncpg ship wheels, so no compiler is needed — only curl
# for the container healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Run as an unprivileged user.
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

LABEL org.opencontainers.image.title="Strix Console — Backend" \
      org.opencontainers.image.description="FastAPI backend for the Strix agentic pentest operations console" \
      org.opencontainers.image.source="https://github.com/usestrix/strix"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
