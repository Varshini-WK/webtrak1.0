from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BackgroundVerification(Base):
    __tablename__ = "background_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    consent_form_signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    identity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NA")
    reference_status: Mapped[str] = mapped_column(String(20), nullable=False, default="NA")
    mail_id_verified: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onboarding_form_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
