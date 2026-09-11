from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import client_ip, require_permission
from app.core.permissions import Permission
from app.models.schedule import Schedule
from app.models.user import User
from app.schemas.common import Message
from app.schemas.schedule import ScheduleCreate, ScheduleOut, ScheduleUpdate
from app.services import audit_service, scheduler_service

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _out(s: Schedule) -> ScheduleOut:
    o = ScheduleOut.model_validate(s)
    o.next_run_at = scheduler_service.next_run(s.cron) if s.enabled else None
    return o


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.SCHEDULE_READ)),
) -> list[ScheduleOut]:
    rows = (await db.execute(select(Schedule).order_by(Schedule.created_at.desc()))).scalars().all()
    return [_out(s) for s in rows]


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    body: ScheduleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.SCHEDULE_MANAGE)),
) -> ScheduleOut:
    if not scheduler_service.validate_cron(body.cron):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cron expression (use 5-field crontab)")
    s = Schedule(
        name=body.name, target=body.target, scan_type=body.scan_type,
        instruction=body.instruction, cron=body.cron, enabled=body.enabled,
        created_by_id=actor.id,
    )
    db.add(s)
    await db.commit()
    scheduler_service.upsert_job(s)
    await audit_service.record(
        db, action="schedule.create", actor=actor, resource_type="schedule",
        resource_id=s.id, ip_address=client_ip(request), detail=f"{s.name} [{s.cron}]",
    )
    return _out(s)


@router.patch("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.SCHEDULE_MANAGE)),
) -> ScheduleOut:
    s = await db.get(Schedule, schedule_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    if body.cron is not None:
        if not scheduler_service.validate_cron(body.cron):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cron expression")
        s.cron = body.cron
    for field in ("name", "target", "scan_type", "instruction", "enabled"):
        val = getattr(body, field)
        if val is not None:
            setattr(s, field, val)
    await db.commit()
    scheduler_service.upsert_job(s)  # re-registers or removes if disabled
    await audit_service.record(
        db, action="schedule.update", actor=actor, resource_type="schedule",
        resource_id=s.id, ip_address=client_ip(request),
    )
    return _out(s)


@router.delete("/{schedule_id}", response_model=Message)
async def delete_schedule(
    schedule_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.SCHEDULE_MANAGE)),
) -> Message:
    s = await db.get(Schedule, schedule_id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    scheduler_service.remove_job(schedule_id)
    await db.delete(s)
    await db.commit()
    await audit_service.record(
        db, action="schedule.delete", actor=actor, resource_type="schedule",
        resource_id=schedule_id, ip_address=client_ip(request),
    )
    return Message(message="Schedule deleted")
