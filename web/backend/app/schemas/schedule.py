from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target: str = Field(min_length=1, max_length=512)
    scan_type: str = "full"
    instruction: str = Field(default="", max_length=4000)
    cron: str = Field(min_length=1, max_length=128)  # 5-field crontab, e.g. "0 2 * * *"
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = None
    target: str | None = None
    scan_type: str | None = None
    instruction: str | None = None
    cron: str | None = None
    enabled: bool | None = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    target: str
    scan_type: str
    instruction: str
    cron: str
    enabled: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
