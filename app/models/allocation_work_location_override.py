from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AllocationWorkLocationOverride(Base):
    __tablename__ = "allocation_work_location_overrides"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    allocation_id: Mapped[int] = mapped_column(ForeignKey("allocations.id"), nullable=False, unique=True)
    work_location_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    allocation = relationship("Allocation", back_populates="work_location_override")
