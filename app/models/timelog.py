from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimeLogStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TimeLog(Base):
    __tablename__ = "time_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    logged_hours: Mapped[float] = mapped_column(Float, nullable=False)
    log_date: Mapped[date] = mapped_column("date", Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TimeLogStatus.SUBMITTED.value, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    project = relationship("Project")

    @property
    def userId(self) -> int:
        return self.user_id

    @property
    def employeeEmail(self) -> str:
        return self.user.email if self.user else ""

    @property
    def projectCode(self) -> str:
        return self.project.projectCode if self.project else ""

    @property
    def hours(self) -> int:
        return int(self.logged_hours)

    @property
    def logDate(self) -> date:
        return self.log_date

    @property
    def managerComment(self) -> str | None:
        return None

    @property
    def reviewedBy(self) -> str | None:
        return None

    @property
    def reviewedAt(self) -> datetime | None:
        return None

    @property
    def createdAt(self) -> datetime:
        return self.created_at

    @property
    def updatedAt(self) -> datetime:
        return self.updated_at
