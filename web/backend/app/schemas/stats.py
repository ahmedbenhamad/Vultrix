from pydantic import BaseModel


class SeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class TimeseriesPoint(BaseModel):
    date: str
    assessments: int
    findings: int


class DashboardStats(BaseModel):
    total_assessments: int
    running_assessments: int
    completed_assessments: int
    total_findings: int
    total_users: int
    severity_breakdown: SeverityBreakdown
    recent_activity: list[TimeseriesPoint]
    findings_by_status: dict[str, int]
