from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PolicyRecipient(Base):
    __tablename__ = "policy_recipients"
    __table_args__ = (UniqueConstraint("policy_id", "user_id", name="uq_policy_recipients_policy_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policy_documents.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    delivery_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="BOTH")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SENT")
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    signed_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    policy = relationship("PolicyDocument", back_populates="recipients")
    user = relationship("User")
