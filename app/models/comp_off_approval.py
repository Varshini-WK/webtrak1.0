from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompOffApproval(Base):
    __tablename__ = "comp_off_approvals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_request_id: Mapped[int] = mapped_column(ForeignKey("user_requests.id"), nullable=False)
    approver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user_request = relationship("UserRequest")
    approver = relationship("User")
