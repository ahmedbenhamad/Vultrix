from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.core.permissions import Permission
from app.models.audit import AuditEvent
from app.models.log import LogEntry
from app.models.user import User
from app.schemas.common import Page
from app.schemas.log import AuditOut, LogOut
from app.services import audit_service

router = APIRouter(tags=["logs"])


@router.get("/audit/verify")
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.AUDIT_READ)),
) -> dict:
    """Recompute the tamper-evident hash chain over the whole audit trail."""
    ok, broken_id = await audit_service.verify_chain(db)
    return {"intact": ok, "first_broken_id": broken_id}


@router.get("/logs", response_model=Page[LogOut])
async def list_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.LOG_READ)),
    level: str | None = Query(default=None),
    assessment_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Page[LogOut]:
    stmt = select(LogEntry)
    if level:
        stmt = stmt.where(LogEntry.level == level)
    if assessment_id:
        stmt = stmt.where(LogEntry.assessment_id == assessment_id)
    if q:
        stmt = stmt.where(func.lower(LogEntry.message).like(f"%{q.lower()}%"))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(
        stmt.order_by(LogEntry.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.scalars().all()
    return Page(items=[LogOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/audit", response_model=Page[AuditOut])
async def list_audit(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.AUDIT_READ)),
    action: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Page[AuditOut]:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if status_filter:
        stmt = stmt.where(AuditEvent.status == status_filter)
    if q:
        stmt = stmt.where(func.lower(AuditEvent.actor_email).like(f"%{q.lower()}%"))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(
        stmt.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.scalars().all()
    return Page(items=[AuditOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)
