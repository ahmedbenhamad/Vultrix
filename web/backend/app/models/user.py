from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # Brute-force protection
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # TOTP MFA
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # sha256 of unused one-time recovery codes, comma-separated
    mfa_recovery_hashes: Mapped[str] = mapped_column(String(2000), default="")

    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    role: Mapped["Role | None"] = relationship(back_populates="users", lazy="joined")  # noqa: F821

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    @property
    def permissions(self) -> list[str]:
        if self.is_superuser:
            from app.core.permissions import ALL_PERMISSIONS

            return list(ALL_PERMISSIONS)
        return self.role.permissions if self.role else []

    def has_permission(self, permission: str) -> bool:
        return self.is_superuser or permission in self.permissions

    @property
    def mfa_required(self) -> bool:
        """True if this user's role makes TOTP MFA mandatory."""
        from app.core.config import settings

        role_name = self.role.name if self.role else ("admin" if self.is_superuser else "")
        return role_name in settings.mfa_required_roles
