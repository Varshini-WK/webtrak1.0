from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    emp_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="INVITED", nullable=False)
    user_type: Mapped[str] = mapped_column(String(50), default="FULLTIME", nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    work_location_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    doj: Mapped[date | None] = mapped_column(Date, nullable=True)
    doi: Mapped[date | None] = mapped_column(Date, nullable=True)
    internship_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band_id: Mapped[int | None] = mapped_column(ForeignKey("bands.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    leave_mappings = relationship("LeaveMapping", back_populates="user", cascade="all, delete-orphan")
    allocations = relationship("Allocation", back_populates="user", cascade="all, delete-orphan")
    band = relationship("Band", back_populates="users")

    # Backward-compatible Prisma-style aliases used by existing services.
    @property
    def empId(self) -> str | None:
        return self.emp_id

    @property
    def userType(self) -> str:
        return self.user_type

    @property
    def phoneNumber(self) -> str | None:
        return self.phone_number

    @property
    def workMode(self) -> str | None:
        return self.work_mode

    @property
    def deliveryStatus(self) -> str | None:
        return self.delivery_status

    @property
    def workLocationType(self) -> str | None:
        return self.work_location_type

    @property
    def bandId(self) -> int | None:
        return self.band_id
