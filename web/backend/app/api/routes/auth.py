from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.database import get_db
from app.core.deps import client_ip, get_current_user
from app.core.rate_limit import limiter
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.core.timeutils import as_utc, now_utc
from app.models.session import UserSession
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    MfaCodeRequest,
    MfaSetupResponse,
    RefreshRequest,
    SessionOut,
    Token,
)
from app.schemas.common import Message
from app.schemas.user import UserOut
from app.services import audit_service, mfa_service, session_service

router = APIRouter(prefix="/auth", tags=["auth"])

MFA_REQUIRED = "MFA_REQUIRED"


def _issue(response: Response, access: str, refresh: str, csrf: str) -> Token:
    set_auth_cookies(response, access, refresh, csrf)
    return Token(access_token=access, refresh_token=refresh)


async def _fail_login(db: AsyncSession, user: User | None, email: str, ip: str, ua: str, reason: str):
    if user is not None:
        user.failed_login_count += 1
        if user.failed_login_count >= settings.MAX_FAILED_LOGINS:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.LOCKOUT_MINUTES)
            user.failed_login_count = 0
        await db.commit()
    await audit_service.record(
        db, action="user.login", actor=user, actor_email=email, ip_address=ip,
        user_agent=ua, status="failure", detail=reason,
    )


@router.post("/login", response_model=Token)
@limiter.limit(settings.LOGIN_RATELIMIT)
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    otp: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> Token:
    ip, ua = client_ip(request), request.headers.get("user-agent", "")
    email = username.lower()
    user = await db.scalar(select(User).where(User.email == email))

    if user and user.locked_until and as_utc(user.locked_until) > now_utc():
        await audit_service.record(
            db, action="user.login", actor=user, ip_address=ip, user_agent=ua,
            status="failure", detail="account locked",
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account temporarily locked. Try again later.")

    if user is None or not verify_password(password, user.password_hash):
        await _fail_login(db, user, email, ip, ua, "invalid credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    if user.mfa_enabled:
        if not otp:
            # Password OK but a second factor is needed; client re-submits with otp.
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MFA_REQUIRED)
        if not mfa_service.verify_mfa(user, otp):
            await _fail_login(db, user, email, ip, ua, "invalid MFA code")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)

    access, refresh, csrf = await session_service.create_session(db, user, ip=ip, user_agent=ua)
    await db.commit()
    await audit_service.record(db, action="user.login", actor=user, ip_address=ip, user_agent=ua)
    return _issue(response, access, refresh, csrf)


@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> Token:
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME) or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
    try:
        payload = decode_token(token)
        if payload.get("type") != REFRESH_TOKEN_TYPE:
            raise ValueError("wrong type")
        user_id, jti = int(payload["sub"]), payload["jti"]
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        access, new_refresh, csrf = await session_service.rotate_session(
            db, user, token, jti, ip=client_ip(request), user_agent=request.headers.get("user-agent", "")
        )
    except session_service.ReuseDetected:
        await db.commit()
        await audit_service.record(
            db, action="user.token_reuse", actor=user, ip_address=client_ip(request),
            status="failure", detail="refresh token reuse detected; all sessions revoked",
        )
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked") from None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from None

    await db.commit()
    return _issue(response, access, new_refresh, csrf)


@router.post("/logout", response_model=Message)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> Message:
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if token:
        try:
            payload = decode_token(token)
            await session_service.revoke_session(db, int(payload["sub"]), payload["jti"])
        except (jwt.PyJWTError, KeyError, ValueError):
            pass
    clear_auth_cookies(response)
    return Message(message="Logged out")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", response_model=Message)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New password too short")
    db_user = await db.get(User, user.id)
    db_user.password_hash = hash_password(body.new_password)
    await db.commit()
    # Force re-auth everywhere after a password change.
    await session_service.revoke_all(db, user.id)
    await audit_service.record(db, action="user.change_password", actor=db_user, ip_address=client_ip(request))
    return Message(message="Password updated. Please sign in again.")


# ── MFA ──────────────────────────────────────────────────────────────────────
@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> MfaSetupResponse:
    db_user = await db.get(User, user.id)
    secret = mfa_service.generate_secret()
    codes = mfa_service.generate_recovery_codes()
    db_user.mfa_secret = secret  # stored but not yet enabled until verified
    db_user.mfa_recovery_hashes = mfa_service.hash_codes(codes)
    await db.commit()
    return MfaSetupResponse(
        secret=secret,
        provisioning_uri=mfa_service.provisioning_uri(secret, db_user.email),
        recovery_codes=codes,
    )


@router.post("/mfa/enable", response_model=Message)
async def mfa_enable(
    body: MfaCodeRequest, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Message:
    db_user = await db.get(User, user.id)
    if not db_user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run MFA setup first")
    if not mfa_service.verify_totp(db_user.mfa_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    db_user.mfa_enabled = True
    await db.commit()
    await audit_service.record(db, action="user.mfa_enable", actor=db_user, ip_address=client_ip(request))
    return Message(message="MFA enabled")


@router.post("/mfa/disable", response_model=Message)
async def mfa_disable(
    body: MfaCodeRequest, request: Request,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> Message:
    db_user = await db.get(User, user.id)
    if not db_user.mfa_enabled or not mfa_service.verify_mfa(db_user, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    if db_user.mfa_required:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA is mandatory for your role")
    db_user.mfa_enabled = False
    db_user.mfa_secret = None
    db_user.mfa_recovery_hashes = ""
    await db.commit()
    await audit_service.record(db, action="user.mfa_disable", actor=db_user, ip_address=client_ip(request))
    return Message(message="MFA disabled")


# ── Sessions ─────────────────────────────────────────────────────────────────
def _current_jti(request: Request) -> str | None:
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not token:
        return None
    try:
        return decode_token(token).get("jti")
    except jwt.PyJWTError:
        return None


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[SessionOut]:
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked == False)  # noqa: E712
        .order_by(UserSession.last_used_at.desc())
    )
    cur = _current_jti(request)
    return [
        SessionOut(
            id=s.id, ip_address=s.ip_address, user_agent=s.user_agent,
            created_at=s.created_at, last_used_at=s.last_used_at, current=(s.jti == cur),
        )
        for s in result.scalars()
    ]


@router.delete("/sessions/{session_id}", response_model=Message)
async def revoke_one_session(
    session_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Message:
    s = await db.get(UserSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    s.revoked = True
    await db.commit()
    return Message(message="Session revoked")


@router.post("/sessions/revoke-all", response_model=Message)
async def revoke_all_sessions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Message:
    await session_service.revoke_all(db, user.id)
    return Message(message="All sessions revoked")
