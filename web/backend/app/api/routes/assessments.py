from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import client_ip, require_permission
from app.core.permissions import Permission
from app.models.assessment import (
    Assessment,
    AssessmentStatus,
    Finding,
    FindingStatus,
    Severity,
)
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentDetail,
    AssessmentSummary,
    DiffFinding,
    FindingOut,
    FindingTriageUpdate,
    ScanDiff,
)
from app.schemas.common import Message, Page
from app.services import audit_service, output_service, strix_service

router = APIRouter(prefix="/assessments", tags=["assessments"])


async def _get_owned_or_404(db: AsyncSession, assessment_id: int, user: User) -> Assessment:
    a = await db.get(Assessment, assessment_id)
    # Hide others' assessments as 404 (no enumeration) unless the user can read all.
    if a is None or (a.created_by_id != user.id and not user.has_permission(Permission.ASSESSMENT_READ_ALL)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return a


@router.get("", response_model=Page[AssessmentSummary])
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSESSMENT_READ)),
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[AssessmentSummary]:
    stmt = select(Assessment)
    # Object-level authz: users see only their own assessments unless they hold read:all.
    if not user.has_permission(Permission.ASSESSMENT_READ_ALL):
        stmt = stmt.where(Assessment.created_by_id == user.id)
    if status_filter:
        stmt = stmt.where(Assessment.status == status_filter)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Assessment.name).like(like) | func.lower(Assessment.target).like(like))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(
        stmt.order_by(Assessment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    rows = result.scalars().all()
    return Page(
        items=[AssessmentSummary.model_validate(a) for a in rows],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=AssessmentDetail, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: AssessmentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ASSESSMENT_CREATE)),
) -> Assessment:
    a = Assessment(
        name=body.name, target=body.target, scan_type=body.scan_type,
        instruction=body.instruction, status=AssessmentStatus.QUEUED,
        phase="queued", created_by=actor,
    )
    a.findings = []  # initialize collections in memory to avoid an async lazy-load
    a.post_ex = []
    db.add(a)
    await db.commit()
    await audit_service.record(
        db, action="assessment.create", actor=actor, resource_type="assessment",
        resource_id=a.id, ip_address=client_ip(request), detail=f"{body.name} -> {body.target}",
    )
    return a


@router.get("/{assessment_id}", response_model=AssessmentDetail)
async def get_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSESSMENT_READ)),
) -> Assessment:
    return await _get_owned_or_404(db, assessment_id, user)


def _finding_key(title: str, cve: str | None) -> str:
    """Identity for diffing: prefer CVE, else normalized title."""
    return (cve or "").strip().lower() or " ".join(title.lower().split())


@router.get("/{assessment_id}/diff", response_model=ScanDiff)
async def diff_assessment(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSESSMENT_READ)),
) -> ScanDiff:
    """Compare this scan's findings against the previous completed scan of the same target."""
    a = await _get_owned_or_404(db, assessment_id, user)

    baseline = await db.scalar(
        select(Assessment)
        .where(
            Assessment.target == a.target,
            Assessment.id != a.id,
            Assessment.id < a.id,
            Assessment.status == AssessmentStatus.COMPLETED,
        )
        .order_by(Assessment.id.desc())
        .limit(1)
    )

    cur = {_finding_key(f.title, f.cve): f for f in a.findings}
    base = {_finding_key(f.title, f.cve): f for f in (baseline.findings if baseline else [])}

    def _d(f: Finding) -> DiffFinding:
        return DiffFinding(title=f.title, severity=f.effective_severity, cve=f.cve)

    return ScanDiff(
        baseline_id=baseline.id if baseline else None,
        baseline_name=baseline.name if baseline else None,
        target=a.target,
        new=[_d(f) for k, f in cur.items() if k not in base],
        fixed=[_d(f) for k, f in base.items() if k not in cur],
        unchanged=[_d(f) for k, f in cur.items() if k in base],
    )


@router.patch("/{assessment_id}/findings/{finding_id}", response_model=FindingOut)
async def triage_finding(
    assessment_id: int,
    finding_id: int,
    body: FindingTriageUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.FINDING_TRIAGE)),
) -> Finding:
    await _get_owned_or_404(db, assessment_id, actor)
    f = await db.get(Finding, finding_id)
    if f is None or f.assessment_id != assessment_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if body.status is not None:
        if body.status not in list(FindingStatus):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        f.status = body.status
    if body.severity_override is not None:
        ov = body.severity_override or None
        if ov and ov not in list(Severity):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid severity")
        f.severity_override = ov
    if body.assignee_id is not None:
        f.assignee_id = body.assignee_id or None
    if body.triage_notes is not None:
        f.triage_notes = body.triage_notes

    await db.commit()
    await audit_service.record(
        db, action="finding.triage", actor=actor, resource_type="finding",
        resource_id=finding_id, ip_address=client_ip(request),
        detail=f"status={f.status} sev={f.effective_severity}",
    )
    await db.refresh(f)
    return f


@router.get("/{assessment_id}/output")
async def get_assessment_output(
    assessment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.ASSESSMENT_READ)),
) -> dict:
    """Strix engine output: agent tree + LLM token/cost telemetry from the run dir."""
    a = await _get_owned_or_404(db, assessment_id, user)
    return output_service.read_output(a)


@router.post("/{assessment_id}/run", response_model=AssessmentDetail)
async def run_assessment(
    assessment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ASSESSMENT_RUN)),
) -> Assessment:
    a = await _get_owned_or_404(db, assessment_id, actor)
    if a.status in (AssessmentStatus.RUNNING, AssessmentStatus.QUEUED) and a.started_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment already active")

    a.status = AssessmentStatus.QUEUED
    a.error = None
    await db.commit()
    strix_service.launch(a.id)  # background runner uses its own sync session
    await audit_service.record(
        db, action="assessment.run", actor=actor, resource_type="assessment",
        resource_id=a.id, ip_address=client_ip(request),
    )
    return a


@router.post("/{assessment_id}/cancel", response_model=AssessmentDetail)
async def cancel_assessment(
    assessment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ASSESSMENT_CANCEL)),
) -> Assessment:
    a = await _get_owned_or_404(db, assessment_id, actor)
    if a.status not in (AssessmentStatus.RUNNING, AssessmentStatus.QUEUED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment is not active")
    a.status = AssessmentStatus.CANCELLED
    await db.commit()
    strix_service.cancel(a.id)  # terminate the underlying engine process if running
    await audit_service.record(
        db, action="assessment.cancel", actor=actor, resource_type="assessment",
        resource_id=a.id, ip_address=client_ip(request),
    )
    return a


@router.delete("/{assessment_id}", response_model=Message)
async def delete_assessment(
    assessment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_permission(Permission.ASSESSMENT_DELETE)),
) -> Message:
    a = await _get_owned_or_404(db, assessment_id, actor)
    await db.delete(a)
    await db.commit()
    await audit_service.record(
        db, action="assessment.delete", actor=actor, resource_type="assessment",
        resource_id=assessment_id, ip_address=client_ip(request),
    )
    return Message(message="Assessment deleted")
