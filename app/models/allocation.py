from datetime import date
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AllocationType(str, Enum):
    STAFFING = "STAFFING"
    DEPLOYABLE = "DEPLOYABLE"
    NONDEPLOYABLE = "NONDEPLOYABLE"
    LOCKED = "LOCKED"
    NONBILLABLE = "NONBILLABLE"


class Allocation(Base):
    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str | None] = mapped_column("designation_role", String(100), nullable=True)
    allocated_hours: Mapped[int] = mapped_column(BigInteger, default=8, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    locked_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user = relationship("User", back_populates="allocations")
    project = relationship("Project", back_populates="allocations")
    override = relationship("AllocationTypeOverride", back_populates="allocation", uselist=False, cascade="all, delete-orphan")
    work_location_override = relationship(
        "AllocationWorkLocationOverride",
        back_populates="allocation",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Backward-compatible Prisma-style aliases used by existing services.
    @property
    def userId(self) -> int:
        return self.user_id

    @property
    def projectCode(self) -> str:
        return self.project.projectCode if self.project else ""

    @property
    def allocatedHours(self) -> int:
        return self.allocated_hours

    @property
    def startDate(self) -> date:
        return self.start_date

    @property
    def endDate(self) -> date | None:
        return self.end_date

    @property
    def isActive(self) -> bool:
        return self.is_active

    @property
    def allocationType(self) -> str:
        if self.override and self.override.allocation_type:
            return self.override.allocation_type
        return AllocationType.LOCKED.value if self.locked_in_date else AllocationType.DEPLOYABLE.value

    @property
    def lockedInDate(self) -> date | None:
        return self.locked_in_date

    @property
    def billingStatus(self) -> str | None:
        return self.billing_status

    @property
    def workLocationType(self) -> str | None:
        if self.work_location_override and self.work_location_override.work_location_type:
            return self.work_location_override.work_location_type
        if self.user and self.user.work_location_type:
            return self.user.work_location_type
        return self.user.work_mode if self.user else None
