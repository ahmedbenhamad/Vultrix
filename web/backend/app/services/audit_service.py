from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import sha256
from app.models.audit import AuditEvent
from app.models.user import User


def _compute_hash(prev_hash: str, ev: AuditEvent) -> str:
    # Only fields stored verbatim (strings/ints) so the hash is stable across a DB
    # round-trip. Order/insertion/deletion tampering is still caught via prev_hash.
    parts = [
        prev_hash,
        str(ev.actor_id or ""),
        ev.actor_email,
        ev.action,
        ev.resource_type,
        ev.resource_id,
        ev.ip_address,
        ev.status,
        ev.detail,
    ]
    return sha256("|".join(parts))


async def record(
    db: AsyncSession,
    *,
    action: str,
    actor: User | None = None,
    actor_email: str = "",
    resource_type: str = "",
    resource_id: str | int = "",
    ip_address: str = "",
    user_agent: str = "",
    detail: str = "",
    status: str = "success",
    commit: bool = True,
) -> AuditEvent:
    """Append a tamper-evident audit event (hash-chained to the previous one)."""
    prev_hash = await db.scalar(
        select(AuditEvent.entry_hash).order_by(AuditEvent.id.desc()).limit(1)
    ) or ""

    event = AuditEvent(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        ip_address=ip_address,
        user_agent=user_agent[:512],
        detail=detail,
        status=status,
        prev_hash=prev_hash,
        created_at=datetime.now(UTC),
    )
    event.entry_hash = _compute_hash(prev_hash, event)
    db.add(event)
    if commit:
        await db.commit()
    return event


async def verify_chain(db: AsyncSession) -> tuple[bool, int | None]:
    """Recompute the chain; returns (ok, first_broken_id)."""
    prev = ""
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.id.asc()))
    for ev in result.scalars():
        if _compute_hash(prev, ev) != ev.entry_hash or ev.prev_hash != prev:
            return False, ev.id
        prev = ev.entry_hash
    return True, None
