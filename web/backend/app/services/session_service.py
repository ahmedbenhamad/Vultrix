"""Server-side session lifecycle: issue, rotate (with reuse detection), revoke."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
    new_jti,
    sha256,
)
from app.core.timeutils import as_utc
from app.models.session import UserSession
from app.models.user import User


class ReuseDetected(Exception):
    """A refresh token that was already rotated was presented again (theft)."""


def _tokens(user: User, jti: str) -> tuple[str, str, str]:
    access = create_access_token(str(user.id), {"email": user.email})
    refresh = create_refresh_token(str(user.id), jti)
    csrf = generate_csrf_token()
    return access, refresh, csrf


async def create_session(
    db: AsyncSession, user: User, *, ip: str, user_agent: str
) -> tuple[str, str, str]:
    """Issue a new session; returns (access, refresh, csrf)."""
    jti = new_jti()
    access, refresh, csrf = _tokens(user, jti)
    db.add(
        UserSession(
            user_id=user.id,
            jti=jti,
            refresh_hash=sha256(refresh),
            user_agent=user_agent[:512],
            ip_address=ip,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return access, refresh, csrf


async def rotate_session(
    db: AsyncSession, user: User, refresh_token: str, jti: str, *, ip: str, user_agent: str
) -> tuple[str, str, str]:
    """Validate + rotate a refresh token. Raises ReuseDetected on theft, ValueError otherwise."""
    sess = await db.scalar(select(UserSession).where(UserSession.jti == jti))
    if sess is None:
        raise ValueError("unknown session")
    if sess.revoked:
        # An already-rotated token is being reused -> revoke the whole family.
        if sess.replaced_by_jti:
            await revoke_all(db, user.id)
            raise ReuseDetected
        raise ValueError("revoked session")
    if as_utc(sess.expires_at) < datetime.now(UTC) or sess.refresh_hash != sha256(refresh_token):
        raise ValueError("invalid session")

    new = new_jti()
    access, refresh, csrf = _tokens(user, new)
    sess.revoked = True
    sess.replaced_by_jti = new
    sess.last_used_at = datetime.now(UTC)
    db.add(
        UserSession(
            user_id=user.id,
            jti=new,
            refresh_hash=sha256(refresh),
            user_agent=user_agent[:512],
            ip_address=ip,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return access, refresh, csrf


async def revoke_session(db: AsyncSession, user_id: int, jti: str) -> bool:
    res = await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.jti == jti, UserSession.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    await db.commit()
    return res.rowcount > 0


async def revoke_all(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    await db.commit()
