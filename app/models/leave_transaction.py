from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LeaveTransaction(Base):
    __tablename__ = "leave_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_request_id: Mapped[int | None] = mapped_column(ForeignKey("user_requests.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    for_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    comments: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user_request = relationship("UserRequest", back_populates="leave_transactions")
    user = relationship("User", foreign_keys=[user_id])
