"""Recurring scans via APScheduler (in-process, sync).

On each cron fire we create a fresh Assessment from the schedule and launch it
through the normal engine path. Jobs are (re)synced from the DB on startup and
whenever a schedule is created/updated/deleted.

Note: single-process only. With multiple web workers you'd get duplicate fires —
move to one dedicated scheduler process (or an APScheduler jobstore + lock) then.
"""

import contextlib
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.assessment import Assessment, AssessmentStatus
from app.models.schedule import Schedule
from app.services import strix_service

logger = logging.getLogger("strix.scheduler")

_scheduler: BackgroundScheduler | None = None


def _job_id(schedule_id: int) -> str:
    return f"sched-{schedule_id}"


def validate_cron(cron: str) -> bool:
    try:
        CronTrigger.from_crontab(cron, timezone="UTC")
        return True
    except (ValueError, TypeError):
        return False


def next_run(cron: str) -> datetime | None:
    try:
        return croniter(cron, datetime.now(UTC)).get_next(datetime)
    except (ValueError, TypeError):
        return None


def start() -> None:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.start()
        logger.info("Scheduler started")


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _fire(schedule_id: int) -> None:
    db = SessionLocal()
    aid: int | None = None
    try:
        s = db.get(Schedule, schedule_id)
        if s is None or not s.enabled:
            return
        a = Assessment(
            name=f"{s.name} (scheduled)", target=s.target, scan_type=s.scan_type,
            instruction=s.instruction, status=AssessmentStatus.QUEUED, phase="queued",
            created_by_id=s.created_by_id,
        )
        db.add(a)
        db.commit()
        s.last_run_at = datetime.now(UTC)
        db.commit()
        aid = a.id
    finally:
        db.close()
    if aid is not None:
        strix_service.launch(aid)


def upsert_job(schedule: Schedule) -> None:
    if _scheduler is None:
        return
    if not schedule.enabled:
        remove_job(schedule.id)
        return
    _scheduler.add_job(
        _fire,
        trigger=CronTrigger.from_crontab(schedule.cron, timezone="UTC"),
        id=_job_id(schedule.id),
        args=[schedule.id],
        replace_existing=True,
        misfire_grace_time=3600,
    )


def remove_job(schedule_id: int) -> None:
    if _scheduler is None:
        return
    with contextlib.suppress(Exception):  # job may not exist
        _scheduler.remove_job(_job_id(schedule_id))


def sync_all() -> None:
    """(Re)register jobs for all enabled schedules — called on startup."""
    db = SessionLocal()
    try:
        for s in db.execute(select(Schedule).where(Schedule.enabled.is_(True))).scalars():
            try:
                upsert_job(s)
            except Exception as e:  # noqa: BLE001
                logger.warning("Skipping invalid schedule %s: %s", s.id, e)
    finally:
        db.close()
