from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.core.permissions import Permission
from app.models.assessment import Assessment, AssessmentStatus, Finding
from app.models.user import User
from app.schemas.stats import (
    DashboardStats,
    SeverityBreakdown,
    TimeseriesPoint,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.STATS_READ)),
) -> DashboardStats:
    total_assessments = await db.scalar(select(func.count(Assessment.id))) or 0
    running = await db.scalar(
        select(func.count(Assessment.id)).where(Assessment.status == AssessmentStatus.RUNNING)
    ) or 0
    completed = await db.scalar(
        select(func.count(Assessment.id)).where(Assessment.status == AssessmentStatus.COMPLETED)
    ) or 0
    total_findings = await db.scalar(select(func.count(Finding.id))) or 0
    total_users = await db.scalar(select(func.count(User.id))) or 0

    sev_counts = dict(
        (await db.execute(select(Finding.severity, func.count(Finding.id)).group_by(Finding.severity))).all()
    )
    breakdown = SeverityBreakdown(
        critical=sev_counts.get("critical", 0),
        high=sev_counts.get("high", 0),
        medium=sev_counts.get("medium", 0),
        low=sev_counts.get("low", 0),
        info=sev_counts.get("info", 0),
    )

    status_counts = dict(
        (await db.execute(select(Assessment.status, func.count(Assessment.id)).group_by(Assessment.status))).all()
    )

    since = datetime.now(UTC) - timedelta(days=13)
    by_day_a: dict[str, int] = defaultdict(int)
    by_day_f: dict[str, int] = defaultdict(int)
    for (created,) in (await db.execute(select(Assessment.created_at).where(Assessment.created_at >= since))).all():
        if created:
            by_day_a[created.date().isoformat()] += 1
    for (created,) in (await db.execute(select(Finding.created_at).where(Finding.created_at >= since))).all():
        if created:
            by_day_f[created.date().isoformat()] += 1

    activity = []
    for i in range(14):
        day = (since + timedelta(days=i)).date().isoformat()
        activity.append(
            TimeseriesPoint(date=day, assessments=by_day_a.get(day, 0), findings=by_day_f.get(day, 0))
        )

    return DashboardStats(
        total_assessments=total_assessments,
        running_assessments=running,
        completed_assessments=completed,
        total_findings=total_findings,
        total_users=total_users,
        severity_breakdown=breakdown,
        recent_activity=activity,
        findings_by_status={str(k): int(v) for k, v in status_counts.items()},
    )
