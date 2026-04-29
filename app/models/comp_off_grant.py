from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompOffGrant(Base):
    __tablename__ = "comp_off_grants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_request_id: Mapped[int | None] = mapped_column(ForeignKey("user_requests.id"), nullable=True)
    grant_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    units: Mapped[float] = mapped_column(nullable=False, default=1.0)
    remaining_units: Mapped[float] = mapped_column(nullable=False, default=1.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    source_request = relationship("UserRequest")
