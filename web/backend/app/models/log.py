from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogEntry(Base):
    """Execution / system log line, optionally tied to an assessment."""

    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(16), default="info", index=True)  # debug/info/warn/error
    source: Mapped[str] = mapped_column(String(64), default="system", index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )
