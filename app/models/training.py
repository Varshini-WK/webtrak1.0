from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Training(Base):
    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    trainers = relationship("TrainingTrainer", back_populates="training", cascade="all, delete-orphan")
    sessions = relationship("TrainingSession", back_populates="training", cascade="all, delete-orphan")
    participants = relationship("TrainingParticipant", back_populates="training", cascade="all, delete-orphan")
    materials = relationship("TrainingMaterial", back_populates="training", cascade="all, delete-orphan")
    assessments = relationship("TrainingAssessment", back_populates="training", cascade="all, delete-orphan")

