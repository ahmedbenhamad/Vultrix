"""Dual data layer.

- **Async** engine + ``AsyncSession`` — used by the FastAPI web app (all routes).
- **Sync** engine + ``SessionLocal`` — used by the background scan runner (threads /
  RQ worker), the seed script, and Alembic, all of which are naturally blocking.

Both point at the same database; we just pick the right driver per URL scheme so
you can run zero-infra on SQLite (aiosqlite/pysqlite) or on Postgres
(asyncpg/psycopg) with the same code.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Deterministic constraint names so Alembic batch migrations (SQLite) work.
_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

_ASYNC_DRIVERS = {"sqlite": "aiosqlite", "postgresql": "asyncpg"}
_SYNC_DRIVERS = {"sqlite": "pysqlite", "postgresql": "psycopg"}


def _with_driver(url_str: str, drivers: dict[str, str]) -> URL:
    u = make_url(url_str)
    backend = u.get_backend_name()  # e.g. "sqlite", "postgresql"
    driver = drivers.get(backend)
    return u.set(drivername=f"{backend}+{driver}") if driver else u


ASYNC_DATABASE_URL = _with_driver(settings.DATABASE_URL, _ASYNC_DRIVERS)
SYNC_DATABASE_URL = _with_driver(settings.DATABASE_URL, _SYNC_DRIVERS)

_sqlite = SYNC_DATABASE_URL.get_backend_name() == "sqlite"
_sync_connect_args = {"check_same_thread": False} if _sqlite else {}


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


# ── async (web) ──────────────────────────────────────────────────────────────
async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# ── sync (worker / seed / alembic) ───────────────────────────────────────────
sync_engine = create_engine(
    SYNC_DATABASE_URL, pool_pre_ping=True, connect_args=_sync_connect_args, future=True
)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False, future=True)
