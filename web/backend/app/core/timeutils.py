"""Timezone helpers.

SQLite doesn't persist tzinfo, so a ``DateTime(timezone=True)`` column round-trips
as a *naive* datetime. Comparing that against an aware ``datetime.now(UTC)`` raises
TypeError. ``as_utc`` coerces naive values to UTC so comparisons are always safe on
both SQLite (dev) and Postgres (prod).
"""

from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
