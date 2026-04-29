from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SubmissionCycle(Base):
    __tablename__ = "submission_cycles"
    __table_args__ = (UniqueConstraint("cycle_key", "scope", name="submission_cycles_cycle_key_scope_key"),)

    SCOPE_GLOBAL = "GLOBAL"
    SCOPE_EMPLOYEE = "EMPLOYEE"
    SCOPE_MANAGER = "MANAGER"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cycle_key: Mapped[str] = mapped_column(String(7), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    window_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manual_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
