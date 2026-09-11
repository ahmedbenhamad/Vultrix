from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.role import RoleOut


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = ""


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role_id: int | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    role_id: int | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str  # already validated on creation; plain str avoids re-validating stored values
    full_name: str = ""
    is_active: bool
    is_superuser: bool
    role: RoleOut | None = None
    permissions: list[str] = []
    mfa_enabled: bool = False
    mfa_required: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
