from datetime import UTC, date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.domain.allocation_rules import BENCH_EQUIVALENT_PROJECT_CODES, BENCH_PROJECT_CODE
from app.models.allocation import Allocation
from app.models.allocation_work_location_override import AllocationWorkLocationOverride
from app.models.allocation_type_override import AllocationTypeOverride
from app.models.project import Project
from app.models.user import User


def _day_start_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


class AllocationRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_id(self, allocation_id: int):
        async with self.db.session() as session:
            return await session.scalar(
                select(Allocation)
                .where(Allocation.id == allocation_id)
                .options(
                    selectinload(Allocation.user),
                    selectinload(Allocation.project),
                    selectinload(Allocation.override),
                    selectinload(Allocation.work_location_override),
                )
            )

    async def find_active_by_user_and_project(self, user_id: int, project_code: str):
        async with self.db.session() as session:
            return await session.scalar(
                select(Allocation)
                .join(Project, Allocation.project_id == Project.id)
                .where(
                    Allocation.user_id == user_id,
                    Project.project_code == project_code,
                    Allocation.is_active.is_(True),
                )
            )

    async def get_active_non_bench_for_user(self, user_id: int, client=None):
        stmt = select(Allocation).where(
            Allocation.user_id == user_id,
            Allocation.is_active.is_(True),
        ).join(Project, Allocation.project_id == Project.id).where(Project.project_code != BENCH_PROJECT_CODE)
        if client is not None:
            return list((await client.scalars(stmt)).all())
        async with self.db.session() as session:
            return list((await session.scalars(stmt)).all())

    async def get_active_bench_for_user(self, user_id: int, client=None):
        stmt = select(Allocation).where(
            Allocation.user_id == user_id,
            Allocation.is_active.is_(True),
        ).join(Project, Allocation.project_id == Project.id).where(Project.project_code == BENCH_PROJECT_CODE)
        if client is not None:
            return list((await client.scalars(stmt)).all())
        async with self.db.session() as session:
            return list((await session.scalars(stmt)).all())

    async def get_active_for_user(self, user_id: int):
        async with self.db.session() as session:
            stmt = (
                select(Allocation)
                .where(Allocation.user_id == user_id, Allocation.is_active.is_(True))
                .options(selectinload(Allocation.project), selectinload(Allocation.user), selectinload(Allocation.override))
                .options(selectinload(Allocation.work_location_override))
            )
            return list((await session.scalars(stmt)).all())

    async def list_active_expired(self, before_date: date):
        async with self.db.session() as session:
            stmt = select(Allocation).where(
                Allocation.is_active.is_(True),
                Allocation.end_date.is_not(None),
                Allocation.end_date < before_date,
            )
            return list((await session.scalars(stmt)).all())

    async def list_active_for_user_on_date(self, user_id: int, on_date: date):
        async with self.db.session() as session:
            stmt = (
                select(Allocation)
                .where(
                    Allocation.user_id == user_id,
                    Allocation.is_active.is_(True),
                    Allocation.start_date <= on_date,
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= on_date),
                )
                .options(selectinload(Allocation.project))
            )
            return list((await session.scalars(stmt)).all())

    async def list_user_ids_with_non_bench_on_dates(self, dates: list[date]) -> list[int]:
        if not dates:
            return []
        min_date = min(dates)
        max_date = max(dates)
        async with self.db.session() as session:
            stmt = (
                select(Allocation.user_id)
                .join(Project, Allocation.project_id == Project.id)
                .where(
                    Allocation.is_active.is_(True),
                    Allocation.start_date <= max_date,
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= min_date),
                    func.upper(Project.project_code).notin_(tuple(BENCH_EQUIVALENT_PROJECT_CODES)),
                )
                .distinct()
                .order_by(Allocation.user_id.asc())
            )
            rows = (await session.scalars(stmt)).all()
            return [int(x) for x in rows]

    async def get_all_for_user_project(self, user_id: int, project_code: str):
        async with self.db.session() as session:
            stmt = (
                select(Allocation)
                .join(Project, Allocation.project_id == Project.id)
                .where(Allocation.user_id == user_id, Project.project_code == project_code)
                .order_by(Allocation.start_date.desc(), Allocation.id.desc())
            )
            return list((await session.scalars(stmt)).all())

    async def create(self, data: dict, client=None):
        payload = {
            "user_id": data["userId"],
            "project_id": None,
            "role": data.get("role"),
            "allocated_hours": data["allocatedHours"],
            "start_date": data["startDate"],
            "end_date": data.get("endDate"),
            "is_active": data.get("isActive", True),
            "locked_in_date": data.get("lockedInDate"),
            "billing_status": data.get("billingStatus"),
        }
        if client is not None:
            project_code = str(data["projectCode"]).strip().upper()
            project = await client.scalar(select(Project).where(Project.project_code == project_code))
            if not project:
                raise ValueError(f"Project does not exist: {project_code}")
            payload["project_id"] = project.id
            row = Allocation(**payload)
            client.add(row)
            await client.flush()
            atype = str(data.get("allocationType", "DEPLOYABLE")).replace("AllocationType.", "").upper()
            if atype in {"NONDEPLOYABLE", "NONBILLABLE"}:
                client.add(AllocationTypeOverride(allocation_id=row.id, allocation_type=atype, reason=f"Allocation override {atype}"))
                await client.flush()
            work_location_type = data.get("workLocationType")
            if work_location_type:
                client.add(
                    AllocationWorkLocationOverride(
                        allocation_id=row.id,
                        work_location_type=str(work_location_type).strip().upper(),
                        reason="Allocation work location override",
                    )
                )
                await client.flush()
            return row
        async with self.db.tx() as session:
            project_code = str(data["projectCode"]).strip().upper()
            project = await session.scalar(select(Project).where(Project.project_code == project_code))
            if not project:
                raise ValueError(f"Project does not exist: {project_code}")
            payload["project_id"] = project.id
            row = Allocation(**payload)
            session.add(row)
            await session.flush()
            atype = str(data.get("allocationType", "DEPLOYABLE")).replace("AllocationType.", "").upper()
            if atype in {"NONDEPLOYABLE", "NONBILLABLE"}:
                session.add(AllocationTypeOverride(allocation_id=row.id, allocation_type=atype, reason=f"Allocation override {atype}"))
                await session.flush()
            work_location_type = data.get("workLocationType")
            if work_location_type:
                session.add(
                    AllocationWorkLocationOverride(
                        allocation_id=row.id,
                        work_location_type=str(work_location_type).strip().upper(),
                        reason="Allocation work location override",
                    )
                )
                await session.flush()
            return row

    async def upsert_work_location_override(self, allocation_id: int, work_location_type: str, client=None):
        normalized = str(work_location_type).strip().upper()
        if client is not None:
            row = await client.scalar(
                select(AllocationWorkLocationOverride).where(AllocationWorkLocationOverride.allocation_id == allocation_id)
            )
            if row is None:
                row = AllocationWorkLocationOverride(
                    allocation_id=allocation_id,
                    work_location_type=normalized,
                    reason="Allocation work location override",
                )
                client.add(row)
            else:
                row.work_location_type = normalized
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.scalar(
                select(AllocationWorkLocationOverride).where(AllocationWorkLocationOverride.allocation_id == allocation_id)
            )
            if row is None:
                row = AllocationWorkLocationOverride(
                    allocation_id=allocation_id,
                    work_location_type=normalized,
                    reason="Allocation work location override",
                )
                session.add(row)
            else:
                row.work_location_type = normalized
            await session.flush()
            return row

    async def deactivate(self, allocation_id: int, end_on: date, client=None):
        if client is not None:
            row = await client.get(Allocation, allocation_id)
            row.is_active = False
            row.end_date = _day_start_utc(end_on)
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.get(Allocation, allocation_id)
            row.is_active = False
            row.end_date = _day_start_utc(end_on)
            await session.flush()
            return row

    async def count_list(
        self,
        *,
        project_code: str | None,
        user_id: int | None,
        search: str | None,
    ) -> int:
        filters = self._list_filters(project_code=project_code, user_id=user_id, search=search)
        async with self.db.session() as session:
            stmt = (
                select(func.count())
                .select_from(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
            )
            if filters:
                stmt = stmt.where(*filters)
            return int((await session.scalar(stmt)) or 0)

    def _list_filters(self, *, project_code: str | None, user_id: int | None, search: str | None) -> list:
        filters: list = [Allocation.is_active.is_(True)]
        if project_code:
            filters.append(Project.project_code == project_code)
        if user_id is not None:
            filters.append(Allocation.user_id == user_id)
        if search and search.strip():
            term = search.strip()
            like = f"%{term}%"
            filters.append(or_(Allocation.role.ilike(like), User.name.ilike(like), User.email.ilike(like), Project.project_code.ilike(like), Project.project_name.ilike(like)))
        return filters

    async def list_page(
        self,
        *,
        project_code: str | None,
        user_id: int | None,
        search: str | None,
        page: int,
        size: int,
    ):
        filters = self._list_filters(project_code=project_code, user_id=user_id, search=search)
        async with self.db.session() as session:
            total_stmt = (
                select(func.count())
                .select_from(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
            )
            if filters:
                total_stmt = total_stmt.where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)
            items_stmt = (
                select(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
                .options(selectinload(Allocation.user), selectinload(Allocation.project), selectinload(Allocation.override))
                .options(selectinload(Allocation.work_location_override))
                .order_by(Allocation.start_date.asc(), Allocation.id.asc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(items_stmt)).all())
            return items, total

    async def find_forecast_page(
        self,
        *,
        cutoff: date,
        project_code: str | None,
        search: str | None,
        page: int,
        size: int,
    ):
        cutoff_dt = _day_start_utc(cutoff)
        today_dt = _day_start_utc(date.today())
        filters = [
            Allocation.is_active.is_(True),
            Allocation.end_date.is_not(None),
            Allocation.end_date >= today_dt,
            Allocation.end_date <= cutoff_dt,
            Project.project_code == project_code if project_code else Project.project_code != BENCH_PROJECT_CODE,
        ]
        if search and search.strip():
            like = f"%{search.strip()}%"
            filters.append(or_(Allocation.role.ilike(like), User.name.ilike(like), User.email.ilike(like)))
        async with self.db.session() as session:
            total_stmt = (
                select(func.count())
                .select_from(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
            )
            total = int((await session.scalar(total_stmt)) or 0)
            items_stmt = (
                select(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
                .options(selectinload(Allocation.user), selectinload(Allocation.project), selectinload(Allocation.override))
                .options(selectinload(Allocation.work_location_override))
                .order_by(Allocation.end_date.asc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(items_stmt)).all())
            return items, total

    async def find_current_bench_page(self, *, search: str | None, page: int, size: int):
        today = date.today()
        today_dt = _day_start_utc(today)
        filters = [
            Allocation.is_active.is_(True),
            func.upper(Project.project_code).in_(tuple(BENCH_EQUIVALENT_PROJECT_CODES)),
            Allocation.start_date <= today_dt,
            or_(Allocation.end_date.is_(None), Allocation.end_date >= today_dt),
        ]
        if search and search.strip():
            like = f"%{search.strip()}%"
            filters.append(or_(Allocation.role.ilike(like), User.name.ilike(like), User.email.ilike(like)))
        async with self.db.session() as session:
            total_stmt = (
                select(func.count())
                .select_from(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
            )
            total = int((await session.scalar(total_stmt)) or 0)
            items_stmt = (
                select(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
                .options(selectinload(Allocation.user), selectinload(Allocation.project), selectinload(Allocation.override))
                .options(selectinload(Allocation.work_location_override))
                .order_by(Allocation.start_date.asc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(items_stmt)).all())
            return items, total

    async def list_bench_equivalent_users_page(
        self, *, search: str | None, page: int, size: int
    ) -> tuple[list[User], dict[int, int], int]:
        """Users with an active allocation today on BENCH or TALENT_POOL (bench-equivalent)."""
        today_dt = _day_start_utc(date.today())
        base_filters = [
            Allocation.is_active.is_(True),
            func.upper(Project.project_code).in_(tuple(BENCH_EQUIVALENT_PROJECT_CODES)),
            Allocation.start_date <= today_dt,
            or_(Allocation.end_date.is_(None), Allocation.end_date >= today_dt),
        ]
        uid_stmt = (
            select(Allocation.user_id)
            .select_from(Allocation)
            .join(Project, Project.id == Allocation.project_id)
            .join(User, User.id == Allocation.user_id)
            .where(*base_filters)
        )
        if search and search.strip():
            term = f"%{search.strip()}%"
            uid_stmt = uid_stmt.where(
                or_(User.name.ilike(term), User.email.ilike(term), User.emp_id.ilike(term)),
            )
        uid_sq = uid_stmt.distinct().subquery()
        async with self.db.session() as session:
            total = int((await session.scalar(select(func.count()).select_from(uid_sq))) or 0)
            if total == 0:
                return [], {}, 0
            user_ids = list(
                (
                    await session.scalars(
                        select(uid_sq.c.user_id).order_by(uid_sq.c.user_id.asc()).offset(page * size).limit(size)
                    )
                ).all()
            )
            if not user_ids:
                return [], {}, total
            users = list(
                (await session.scalars(select(User).where(User.id.in_(user_ids)).order_by(User.name.asc(), User.id.asc()))).all()
            )
            sum_rows = (
                await session.execute(
                    select(Allocation.user_id, func.sum(Allocation.allocated_hours))
                    .select_from(Allocation)
                    .join(Project, Project.id == Allocation.project_id)
                    .where(
                        Allocation.user_id.in_(user_ids),
                        *base_filters,
                    )
                    .group_by(Allocation.user_id)
                )
            ).all()
        hours_by_user = {int(uid): int(h or 0) for uid, h in sum_rows}
        return users, hours_by_user, total
