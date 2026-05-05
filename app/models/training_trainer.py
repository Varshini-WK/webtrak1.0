from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingTrainer(Base):
    __tablename__ = "training_trainers"
    __table_args__ = (UniqueConstraint("training_id", "trainer_user_id", name="uq_training_trainers_training_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False)
    trainer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    training = relationship("Training", back_populates="trainers")

