from __future__ import annotations

from datetime import date

from sqlalchemy import case, func, or_, select

from app.domain.employee_status import EmployeeStatus
from app.models.allocation import Allocation
from app.models.attrition import Attrition
from app.models.band import Band
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

_MANAGER_ROLE_NAMES = ("MANAGER", "ROLE_MANAGER")


class AttritionRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_user_id(self, *, user_id: int) -> Attrition | None:
        async with self.db.session() as session:
            return await session.scalar(select(Attrition).where(Attrition.user_id == user_id))

    async def list_with_users_for_date_range(
        self,
        *,
        start_inclusive: date,
        end_inclusive: date,
    ) -> list[tuple[Attrition, User]]:
        async with self.db.session() as session:
            stmt = (
                select(Attrition, User)
                .join(User, User.id == Attrition.user_id)
                .where(
                    Attrition.last_working_day >= start_inclusive,
                    Attrition.last_working_day <= end_inclusive,
                )
                .order_by(Attrition.last_working_day.asc(), Attrition.id.asc())
            )
            return list((await session.execute(stmt)).all())

    async def count_users_with_statuses(self, *, statuses: list[str]) -> int:
        """Headcount: users whose ``status`` is in ``statuses`` (e.g. active workforce / in-office roster)."""
        if not statuses:
            return 0
        async with self.db.session() as session:
            stmt = select(func.count()).select_from(User).where(User.status.in_(statuses))
            return int((await session.scalar(stmt)) or 0)

    async def manager_user_ids_for_project(self, *, project_id: int) -> str | None:
        """All users with MANAGER / ROLE_MANAGER on this project; comma-separated ``users.id``, ascending."""
        async with self.db.session() as session:
            stmt = (
                select(User.id)
                .select_from(UserRole)
                .join(Role, UserRole.role_id == Role.id)
                .join(User, User.id == UserRole.user_id)
                .where(UserRole.project_id == project_id, Role.name.in_(_MANAGER_ROLE_NAMES))
                .distinct()
                .order_by(User.id.asc())
            )
            ids = [int(i) for i in (await session.scalars(stmt)).all()]
            if not ids:
                return None
            return ", ".join(str(i) for i in ids)

    async def primary_project_id_before_exit(self, *, user_id: int, last_working_day: date) -> int | None:
        """Project from allocation active on LWD; prefer non-BENCH; else most recently ended allocation."""
        async with self.db.session() as session:
            bench_rank = case((func.upper(Project.project_code) == "BENCH", 1), else_=0)
            stmt_active = (
                select(Allocation.project_id)
                .join(Project, Project.id == Allocation.project_id)
                .where(
                    Allocation.user_id == user_id,
                    Allocation.start_date <= last_working_day,
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= last_working_day),
                )
                .order_by(bench_rank.asc(), Allocation.start_date.desc(), Allocation.id.desc())
                .limit(1)
            )
            pid = await session.scalar(stmt_active)
            if pid is not None:
                return int(pid)

            stmt_past = (
                select(Allocation.project_id)
                .where(
                    Allocation.user_id == user_id,
                    Allocation.end_date.isnot(None),
                    Allocation.end_date <= last_working_day,
                )
                .order_by(Allocation.end_date.desc(), Allocation.id.desc())
                .limit(1)
            )
            pid2 = await session.scalar(stmt_past)
            return int(pid2) if pid2 is not None else None

    async def build_band_snapshots(self, *, user: User) -> tuple[str | None, str | None, str | None]:
        """Returns (band_name, designation, band_role). band_role is role/designation only (same as designation)."""
        designation = (user.role or "").strip() or None
        band_name: str | None = None
        async with self.db.session() as session:
            if user.band_id is not None:
                band = await session.get(Band, user.band_id)
                if band is not None:
                    band_name = (band.name or "").strip() or None
        band_role = designation
        return band_name, designation, band_role

    async def resolve_project_manager_label(self, *, user_id: int, last_working_day: date) -> str | None:
        """Comma-separated manager ``users.id`` for the employee's primary project at exit (see ``primary_project_id_before_exit``)."""
        pid = await self.primary_project_id_before_exit(user_id=user_id, last_working_day=last_working_day)
        if pid is None:
            return None
        return await self.manager_user_ids_for_project(project_id=pid)

    async def upsert_for_user(
        self,
        *,
        user_id: int,
        actor_id: int,
        payload: dict,
    ) -> Attrition:
        async with self.db.tx() as session:
            row = await session.scalar(select(Attrition).where(Attrition.user_id == user_id))
            if row is None:
                row = Attrition(user_id=user_id, created_by=actor_id, **payload)
                session.add(row)
            else:
                for k, v in payload.items():
                    setattr(row, k, v)
            user_entity = await session.get(User, user_id)
            if user_entity is not None:
                user_entity.status = EmployeeStatus.OFFBOARDED.value
            await session.flush()
            return row

    async def get_user_by_emp_id(self, *, emp_id: str) -> User | None:
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.emp_id == emp_id))
