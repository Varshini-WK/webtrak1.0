from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    training = relationship("Training", back_populates="sessions")
    attendance_rows = relationship("TrainingAttendance", back_populates="session", cascade="all, delete-orphan")

