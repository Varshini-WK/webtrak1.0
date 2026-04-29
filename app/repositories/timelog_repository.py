from datetime import UTC, date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.role import Role
from app.models.timelog import TimeLog
from app.models.user import User
from app.models.user_role import UserRole


def _now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimeLogRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_user_by_email(self, email: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def project_exists(self, project_code: str) -> bool:
        async with self.db.session() as session:
            row = await session.scalar(select(Project.id).where(Project.project_code == project_code))
            return row is not None

    async def sum_hours_for_user_on_dates(self, user_id: int, dates: list[date]) -> float:
        if not dates:
            return 0.0
        async with self.db.session() as session:
            stmt = select(func.coalesce(func.sum(TimeLog.logged_hours), 0.0)).where(
                TimeLog.user_id == user_id,
                TimeLog.log_date.in_(dates),
            )
            return float((await session.scalar(stmt)) or 0.0)

    async def create_timelog(self, data: dict, client=None):
        project_code = str(data["projectCode"]).strip().upper()
        payload = {
            "user_id": data["userId"],
            "project_id": None,
            "log_date": data["logDate"],
            "logged_hours": data["hours"],
            "description": data.get("description"),
            "status": data.get("status", "SUBMITTED"),
            "created_at": data.get("createdAt", _now_utc()),
            "updated_at": data.get("updatedAt", _now_utc()),
        }
        if client is not None:
            project = await client.scalar(select(Project).where(Project.project_code == project_code))
            if not project:
                raise ValueError(f"Project not found: {project_code}")
            payload["project_id"] = project.id
            row = TimeLog(**payload)
            client.add(row)
            await client.flush()
            return await client.scalar(
                select(TimeLog)
                .where(TimeLog.id == row.id)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )
        async with self.db.tx() as session:
            project = await session.scalar(select(Project).where(Project.project_code == project_code))
            if not project:
                raise ValueError(f"Project not found: {project_code}")
            payload["project_id"] = project.id
            row = TimeLog(**payload)
            session.add(row)
            await session.flush()
            return await session.scalar(
                select(TimeLog)
                .where(TimeLog.id == row.id)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )

    async def get_by_id(self, timelog_id: int):
        async with self.db.session() as session:
            return await session.scalar(
                select(TimeLog).where(TimeLog.id == timelog_id).options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )

    async def update_timelog(self, timelog_id: int, data: dict, client=None):
        async def _apply_updates(row, session_like):
            for k, v in data.items():
                if k == "project_code":
                    project = await session_like.scalar(select(Project).where(Project.project_code == str(v).strip().upper()))
                    if not project:
                        raise ValueError(f"Project not found: {v}")
                    row.project_id = project.id
                elif k == "hours":
                    row.logged_hours = float(v)
                elif k == "log_date":
                    row.log_date = v
                elif k in {"manager_comment", "reviewed_by", "reviewed_at"}:
                    # Java parity model does not persist reviewer/comment fields.
                    continue
                elif k == "updated_at":
                    row.updated_at = v
                elif hasattr(row, k):
                    setattr(row, k, v)
            row.updated_at = _now_utc()

        if client is not None:
            row = await client.get(TimeLog, timelog_id)
            await _apply_updates(row, client)
            await client.flush()
            return await client.scalar(
                select(TimeLog)
                .where(TimeLog.id == timelog_id)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )
        async with self.db.tx() as session:
            row = await session.get(TimeLog, timelog_id)
            await _apply_updates(row, session)
            await session.flush()
            return await session.scalar(
                select(TimeLog)
                .where(TimeLog.id == timelog_id)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )

    async def delete_timelog(self, timelog_id: int, client=None) -> None:
        if client is not None:
            row = await client.get(TimeLog, timelog_id)
            if row:
                await client.delete(row)
                await client.flush()
            return
        async with self.db.tx() as session:
            row = await session.get(TimeLog, timelog_id)
            if row:
                await session.delete(row)
                await session.flush()

    async def list_employee_timelogs(self, employee_email: str, page: int, size: int):
        async with self.db.session() as session:
            total_stmt = (
                select(func.count())
                .select_from(TimeLog)
                .join(User, TimeLog.user_id == User.id)
                .where(User.email == employee_email)
            )
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                select(TimeLog)
                .join(User, TimeLog.user_id == User.id)
                .where(User.email == employee_email)
                .order_by(TimeLog.log_date.desc(), TimeLog.id.desc())
                .offset(page * size)
                .limit(size)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )
            items = list((await session.scalars(stmt)).all())
            return items, total

    async def list_employee_timelogs_by_date(
        self,
        employee_email: str,
        log_date: date,
        page: int,
        size: int,
        allowed_project_codes: list[str] | None = None,
    ):
        async with self.db.session() as session:
            total_stmt = (
                select(func.count())
                .select_from(TimeLog)
                .join(User, TimeLog.user_id == User.id)
                .join(Project, TimeLog.project_id == Project.id)
                .where(User.email == employee_email, TimeLog.log_date == log_date)
            )
            if allowed_project_codes is not None:
                if not allowed_project_codes:
                    return [], 0
                total_stmt = total_stmt.where(Project.project_code.in_(allowed_project_codes))
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                select(TimeLog)
                .join(User, TimeLog.user_id == User.id)
                .join(Project, TimeLog.project_id == Project.id)
                .where(User.email == employee_email, TimeLog.log_date == log_date)
                .order_by(TimeLog.id.desc())
                .offset(page * size)
                .limit(size)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )
            if allowed_project_codes is not None:
                stmt = stmt.where(Project.project_code.in_(allowed_project_codes))
            items = list((await session.scalars(stmt)).all())
            return items, total

    async def get_manager_project_codes(self, manager_user_id: int) -> list[str]:
        async with self.db.session() as session:
            stmt = (
                select(Project.project_code)
                .select_from(UserRole)
                .join(Role, Role.id == UserRole.role_id)
                .join(Project, Project.id == UserRole.project_id)
                .where(
                    UserRole.user_id == manager_user_id,
                    Role.name.in_(["ROLE_MANAGER", "MANAGER"]),
                )
            )
            rows = (await session.scalars(stmt)).all()
            return sorted({row for row in rows if row})

    async def is_manager_for_project(self, manager_user_id: int, project_code: str) -> bool:
        async with self.db.session() as session:
            stmt = (
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .join(Project, Project.id == UserRole.project_id)
                .where(
                    UserRole.user_id == manager_user_id,
                    Project.project_code == project_code,
                    Role.name.in_(["ROLE_MANAGER", "MANAGER"]),
                )
            )
            row = await session.scalar(stmt)
            return row is not None

    async def update_status_single(self, timelog_id: int, status_value: str, manager_comment: str | None, actor_email: str):
        async with self.db.tx() as session:
            row = await session.get(TimeLog, timelog_id)
            if not row:
                return None
            row.status = status_value
            row.updated_at = _now_utc()
            await session.flush()
            return await session.scalar(
                select(TimeLog)
                .where(TimeLog.id == timelog_id)
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
            )

    async def update_status_batch(
        self,
        *,
        employee_email: str,
        project_code: str,
        log_date: date,
        status_value: str,
        manager_comment: str | None,
        actor_email: str,
    ) -> list[TimeLog]:
        _ = manager_comment, actor_email
        project_code = project_code.strip().upper()
        async with self.db.tx() as session:
            rows = (
                await session.scalars(
                    select(TimeLog)
                    .join(User, TimeLog.user_id == User.id)
                    .join(Project, TimeLog.project_id == Project.id)
                    .where(User.email == employee_email, Project.project_code == project_code, TimeLog.log_date == log_date)
                )
            ).all()
            for row in rows:
                row.status = status_value
                row.updated_at = _now_utc()
            await session.flush()
            return list(rows)

    async def export_logs(
        self,
        *,
        project_code: str | None,
        employee_email: str | None,
        start_date: date,
        end_date: date,
    ) -> list[TimeLog]:
        filters = [TimeLog.log_date >= start_date, TimeLog.log_date <= end_date]
        if project_code:
            filters.append(Project.project_code == project_code)
        if employee_email:
            filters.append(User.email == employee_email)
        async with self.db.session() as session:
            stmt = (
                select(TimeLog)
                .join(User, TimeLog.user_id == User.id)
                .join(Project, TimeLog.project_id == Project.id)
                .where(and_(*filters))
                .options(selectinload(TimeLog.user), selectinload(TimeLog.project))
                .order_by(TimeLog.log_date.asc(), Project.project_code.asc(), User.email.asc(), TimeLog.id.asc())
            )
            return list((await session.scalars(stmt)).all())
