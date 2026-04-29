from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KpiDefinition(Base):
    __tablename__ = "kpi_definitions"
    __table_args__ = (
        UniqueConstraint(
            "band_id",
            "department",
            "designation",
            "kpi_name",
            name="kpi_definitions_band_department_designation_kpi_name_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    band_id: Mapped[int] = mapped_column(ForeignKey("bands.id"), nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    kpi_name: Mapped[str] = mapped_column(String(255), nullable=False)
    weightage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    band = relationship("Band", back_populates="kpi_definitions")
