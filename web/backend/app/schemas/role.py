from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    description: str = ""


class RoleCreate(RoleBase):
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    description: str | None = None
    permissions: list[str] | None = None


class RoleOut(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_system: bool
    permissions: list[str]
    created_at: datetime


class PermissionOut(BaseModel):
    key: str
    description: str


class PermissionCatalog(BaseModel):
    permissions: list[PermissionOut]
