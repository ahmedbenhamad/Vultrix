from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserSession(Base):
    """Server-side record of an issued refresh token (one per login).

    Enables refresh-token **rotation** (each refresh mints a new jti and revokes
    the old), **reuse detection** (a refresh presenting an already-rotated jti
    means theft → revoke the whole chain), and **remote revocation** ("sign out
    everywhere" / per-session revoke from the UI).
    """

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    refresh_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 of the token

    user_agent: Mapped[str] = mapped_column(String(512), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # jti this session was rotated into; a refresh of a rotated jti = reuse/theft
    replaced_by_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
