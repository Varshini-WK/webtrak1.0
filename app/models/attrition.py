from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Attrition(Base):
    __tablename__ = "attritions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    separation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    critical_skill: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_regretted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_working_day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    band_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    band_role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Role/designation only at exit (users.role snapshot); not prefixed with band name.",
    )
    project_manager: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Comma-separated manager users.id values on primary project at LWD.",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
