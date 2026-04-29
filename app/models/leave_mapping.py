from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LeaveMapping(Base):
    __tablename__ = "leave_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_leave: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    secondary_leave: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    carry_forward: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user = relationship("User", back_populates="leave_mappings")
