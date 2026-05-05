from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Band(Base):
    __tablename__ = "bands"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # stream: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # designation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    users = relationship("User", back_populates="band")
    kpi_definitions = relationship("KpiDefinition", back_populates="band")
    designations = relationship("Designation", back_populates="band")
