from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PostExKind(StrEnum):
    SESSION = "session"           # a shell / session was opened
    PRIVESC = "privesc"           # privilege escalation
    PERSISTENCE = "persistence"   # persistence mechanism installed
    LATERAL = "lateral"           # lateral movement to another host
    EXFIL = "exfil"               # data exfiltration / loot
    CREDENTIAL = "credential"     # credentials harvested


class PostExEvent(Base):
    """A post-exploitation activity recorded during an assessment."""

    __tablename__ = "post_ex_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    assessment: Mapped["Assessment"] = relationship(back_populates="post_ex")  # noqa: F821

    kind: Mapped[str] = mapped_column(String(24), default=PostExKind.SESSION, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    host: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
