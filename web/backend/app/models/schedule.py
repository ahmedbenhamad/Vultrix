from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Schedule(Base):
    """A recurring assessment definition fired on a cron schedule."""

    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(512), nullable=False)
    scan_type: Mapped[str] = mapped_column(String(64), default="full")
    instruction: Mapped[str] = mapped_column(Text, default="")

    cron: Mapped[str] = mapped_column(String(128), nullable=False)  # 5-field crontab
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped["User | None"] = relationship(lazy="joined")  # noqa: F821

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
