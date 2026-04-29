from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    yoe: Mapped[int | None] = mapped_column(nullable=True)
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    secondary_skills: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    personal_resume: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    aadhaar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pan_card: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user = relationship("User", back_populates="profile")

    @property
    def userId(self) -> int:
        return self.user_id

    @property
    def primarySkills(self) -> list[str] | None:
        return self.primary_skills

    @property
    def secondarySkills(self) -> list[dict[str, Any]] | None:
        return self.secondary_skills

    @property
    def personalResume(self) -> str | None:
        return self.personal_resume

    @property
    def profilePhoto(self) -> str | None:
        return self.profile_photo

    @property
    def panCard(self) -> str | None:
        return self.pan_card
