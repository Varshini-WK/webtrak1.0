from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRequest(Base):
    __tablename__ = "user_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    request_from_date: Mapped[date] = mapped_column(Date, nullable=False)
    request_to_date: Mapped[date] = mapped_column(Date, nullable=False)
    request_type: Mapped[str] = mapped_column(String(20), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_half_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reference_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    manager_comp_off_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User")
    trackings = relationship("UserRequestTracking", back_populates="user_request", cascade="all, delete-orphan")
    leave_transactions = relationship("LeaveTransaction", back_populates="user_request")
