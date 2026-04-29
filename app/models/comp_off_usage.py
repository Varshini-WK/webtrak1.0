from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompOffUsage(Base):
    __tablename__ = "comp_off_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grant_id: Mapped[int] = mapped_column(ForeignKey("comp_off_grants.id"), nullable=False)
    user_request_id: Mapped[int] = mapped_column(ForeignKey("user_requests.id"), nullable=False)
    used_units: Mapped[float] = mapped_column(nullable=False)
    used_for_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    grant = relationship("CompOffGrant")
    user_request = relationship("UserRequest")
