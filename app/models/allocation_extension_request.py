from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AllocationExtensionRequest(Base):
    __tablename__ = "allocation_extension_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    allocation_id: Mapped[int] = mapped_column(ForeignKey("allocations.id"), nullable=False)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    allocation = relationship("Allocation")
    requested_by = relationship("User")
