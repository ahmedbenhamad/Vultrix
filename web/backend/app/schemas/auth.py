from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    # Optional: browser clients use the httpOnly cookie instead.
    refresh_token: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    otp: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ── MFA ──────────────────────────────────────────────────────────────────────
class MfaSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    recovery_codes: list[str]  # shown once, at setup


class MfaCodeRequest(BaseModel):
    code: str


# ── Sessions ─────────────────────────────────────────────────────────────────
class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    user_agent: str
    created_at: datetime
    last_used_at: datetime
    current: bool = False
