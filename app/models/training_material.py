from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingMaterial(Base):
    __tablename__ = "training_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    material_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    visibility: Mapped[str] = mapped_column(String(50), nullable=False, default="EMPLOYEE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    training = relationship("Training", back_populates="materials")

