"""Reusable FastAPI dependencies: current user resolution and RBAC guards.

Auth accepts a token from either the httpOnly access **cookie** (browser SPA) or an
``Authorization: Bearer`` header (API clients / transitional). Cookie is preferred.
"""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.models.user import User

# auto_error=False so a missing header isn't a hard failure — we also check the cookie.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)

_CRED_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def _extract_token(request: Request, bearer: str | None) -> str | None:
    return request.cookies.get(settings.ACCESS_COOKIE_NAME) or bearer


async def get_current_user(
    request: Request,
    bearer: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_token(request, bearer)
    if not token:
        raise _CRED_EXC
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            raise _CRED_EXC
        user_id = int(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise _CRED_EXC from None

    user = await db.get(User, user_id)
    if user is None:
        raise _CRED_EXC
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_permission(permission: str) -> Callable[[User], User]:
    """Return a dependency that enforces a single permission on the current user."""

    def _guard(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return user

    return _guard


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""
