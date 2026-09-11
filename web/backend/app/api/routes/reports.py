from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import client_ip, require_permission
from app.core.permissions import Permission
from app.models.assessment import Assessment
from app.models.report import Report
from app.models.user import User
from app.schemas.common import Page
from app.schemas.report import ReportOut
from app.services import audit_service, report_export

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=Page[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.REPORT_READ)),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[ReportOut]:
    stmt = select(Report)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(
        stmt.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.scalars().all()
    return Page(items=[ReportOut.model_validate(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/assessment/{assessment_id}/export")
async def export_assessment_report(
    assessment_id: int,
    request: Request,
    fmt: str = Query(default="pdf", pattern="^(pdf|csv|json)$"),
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.REPORT_EXPORT)),
) -> Response:
    a = await db.get(Assessment, assessment_id)
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    exporter, media_type = report_export.EXPORTERS[fmt]
    try:
        content = exporter(a)  # findings are selectin-eager-loaded by db.get
    except ImportError as e:  # pragma: no cover - reportlab missing
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Export format '{fmt}' unavailable: {e}",
        ) from e

    await audit_service.record(
        db, action="report.export", actor=actor, resource_type="assessment",
        resource_id=assessment_id, ip_address=client_ip(request), detail=f"format={fmt}",
    )
    filename = f"assessment-{assessment_id}-report.{fmt}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
