from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    project_type: Mapped[str] = mapped_column(String(50), default="IN_HOUSE", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_manager_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    user_roles = relationship("UserRole", back_populates="project")
    allocations = relationship("Allocation", back_populates="project")
    account_manager = relationship("User", foreign_keys=[account_manager_user_id])

    @property
    def projectCode(self) -> str:
        return self.project_code

    @property
    def projectName(self) -> str:
        return self.project_name

    @property
    def projectType(self) -> str:
        return self.project_type

    @property
    def isActive(self) -> bool:
        return self.is_active
