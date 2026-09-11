from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    severity: str
    effective_severity: str
    cve: str | None = None
    description: str
    recommendation: str
    evidence: str
    status: str = "open"
    severity_override: str | None = None
    assignee_id: int | None = None
    triage_notes: str = ""
    created_at: datetime


class FindingTriageUpdate(BaseModel):
    status: str | None = None
    severity_override: str | None = None
    assignee_id: int | None = None
    triage_notes: str | None = None


class DiffFinding(BaseModel):
    title: str
    severity: str
    cve: str | None = None


class ScanDiff(BaseModel):
    baseline_id: int | None = None
    baseline_name: str | None = None
    target: str
    new: list[DiffFinding] = []
    fixed: list[DiffFinding] = []
    unchanged: list[DiffFinding] = []


class PostExOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    detail: str
    evidence: str
    host: str
    created_at: datetime


class AssessmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=512)
    scan_type: str = "full"
    instruction: str = Field(default="", max_length=4000)


class AssessmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target: str
    scan_type: str
    status: str
    phase: str
    progress: float
    findings_count: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AssessmentDetail(AssessmentSummary):
    strix_run_id: str | None = None
    error: str | None = None
    instruction: str = ""
    findings: list[FindingOut] = []
    post_ex: list[PostExOut] = []
