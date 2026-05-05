from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingParticipant(Base):
    __tablename__ = "training_participants"
    __table_args__ = (UniqueConstraint("training_id", "user_id", name="uq_training_participants_training_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    participant_source: Mapped[str] = mapped_column(String(50), nullable=False)
    enrollment_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    training = relationship("Training", back_populates="participants")

