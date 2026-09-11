from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    assessment_id: int | None = None
    summary: str
    created_at: datetime


class ReportCreate(BaseModel):
    title: str
    assessment_id: int | None = None
    summary: str = ""
