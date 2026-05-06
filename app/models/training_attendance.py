from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingAttendance(Base):
    __tablename__ = "training_attendance"
    __table_args__ = (UniqueConstraint("training_session_id", "user_id", name="uq_training_attendance_session_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    attendance_status: Mapped[str] = mapped_column(String(50), nullable=False)
    marked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    marked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("TrainingSession", back_populates="attendance_rows")

