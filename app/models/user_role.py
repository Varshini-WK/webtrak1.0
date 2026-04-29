from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), primary_key=True)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    project = relationship("Project", back_populates="user_roles")

    @property
    def userId(self) -> int:
        return self.user_id

    @property
    def roleId(self) -> int:
        return self.role_id

    @property
    def projectCode(self) -> str | None:
        return self.project.projectCode if self.project else None
