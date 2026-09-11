from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    source: str
    message: str
    assessment_id: int | None = None
    created_at: datetime


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_email: str
    action: str
    resource_type: str
    resource_id: str
    ip_address: str
    status: str
    detail: str
    created_at: datetime
