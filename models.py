"""
SQLAlchemy ORM models — Lead and SessionLog.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime

from database import Base


class Lead(Base):
    """A prospective student captured through the enrollment flow."""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    wa_number = Column(String(30), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False)
    course_interest = Column(String(200), nullable=False)
    preferred_time = Column(String(200), nullable=True)
    status = Column(String(20), default="new")  # new | contacted | enrolled
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "wa_number": self.wa_number,
            "name": self.name,
            "phone": self.phone,
            "course_interest": self.course_interest,
            "preferred_time": self.preferred_time,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SessionLog(Base):
    """Optional — persists conversation state across server restarts."""

    __tablename__ = "session_logs"

    id = Column(Integer, primary_key=True, index=True)
    wa_number = Column(String(30), unique=True, nullable=False, index=True)
    context_json = Column(Text, default="{}")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
