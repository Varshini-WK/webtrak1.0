from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRequestTracking(Base):
    __tablename__ = "user_request_tracking"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    user_request_id: Mapped[int] = mapped_column(ForeignKey("user_requests.id"), nullable=False)
    actioner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user_request = relationship("UserRequest", back_populates="trackings")
    actioner = relationship("User")
    project = relationship("Project")
