import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import settings
from app.core.middleware import (
    CSRFMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("strix.console")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema + seed run on the sync engine; keep it off the event loop.
    from app.core import events
    from app.db.seed import run as seed_run
    from app.services import strix_service

    # Let the (threaded) scan runner publish live events onto this loop.
    events.set_loop(asyncio.get_running_loop())

    try:
        await asyncio.to_thread(seed_run)
    except Exception as e:  # noqa: BLE001
        logger.warning("Seed on startup skipped/failed: %s", e)

    # Reconcile assessments left "running" by a previous process (Phase 2 will
    # reattach; for now mark them failed so the UI isn't stuck).
    try:
        await asyncio.to_thread(strix_service.reconcile_orphans)
    except Exception as e:  # noqa: BLE001
        logger.warning("Orphan reconcile skipped: %s", e)

    # Start the recurring-scan scheduler and register enabled schedules.
    from app.services import scheduler_service

    try:
        scheduler_service.start()
        await asyncio.to_thread(scheduler_service.sync_all)
    except Exception as e:  # noqa: BLE001
        logger.warning("Scheduler start skipped: %s", e)

    yield

    with contextlib.suppress(Exception):
        scheduler_service.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    lifespan=lifespan,
)

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Order matters: CORS outermost, then request-id, security headers, CSRF, rate limit.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # cookies require a specific origin list (not "*")
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-Request-ID"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "version": __version__}


@app.get("/livez", tags=["system"])
def livez() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/readyz", tags=["system"])
async def readyz() -> JSONResponse:
    """Readiness: DB connectivity + engine configuration. Returns 503 if not ready."""
    from sqlalchemy import text

    from app.core.database import AsyncSessionLocal
    from app.services import strix_service

    checks: dict[str, object] = {}
    ok = True
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["database"] = f"error: {type(e).__name__}"
        ok = False

    engine_ok, reason = strix_service._engine_available()
    checks["engine"] = "real" if engine_ok else f"simulation ({reason})"
    checks["version"] = __version__

    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ready" if ok else "not_ready", "checks": checks},
    )
