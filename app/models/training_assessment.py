from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingAssessment(Base):
    __tablename__ = "training_assessments"
    __table_args__ = (UniqueConstraint("training_id", "name", name="uq_training_assessment_training_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    weight_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    training = relationship("Training", back_populates="assessments")

