from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.allocation import Allocation
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def _map_project_write_keys(data: dict) -> dict:
    keymap = {
        "projectCode": "project_code",
        "projectName": "project_name",
        "projectType": "project_type",
        "isActive": "is_active",
    }
    return {keymap.get(k, k): v for k, v in data.items()}


class ProjectRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_code(self, project_code: str):
        async with self.db.session() as session:
            return await session.scalar(select(Project).where(Project.project_code == project_code))

    async def get_by_name_case_insensitive(self, project_name: str):
        async with self.db.session() as session:
            return await session.scalar(select(Project).where(func.lower(Project.project_name) == project_name.lower()))

    async def create_project(self, data: dict, client=None):
        payload = _map_project_write_keys(data)
        if client is None:
            async with self.db.tx() as session:
                row = Project(**payload)
                session.add(row)
                await session.flush()
                return row
        row = Project(**payload)
        client.add(row)
        await client.flush()
        return row

    async def list_projects(self, page: int, size: int, search: str | None, exclude_codes: list[str]):
        filters = []
        if exclude_codes:
            filters.append(Project.project_code.notin_(exclude_codes))
        if search:
            term = f"%{search}%"
            filters.append(or_(Project.project_code.ilike(term), Project.project_name.ilike(term)))
        async with self.db.session() as session:
            total_stmt = select(func.count()).select_from(Project)
            items_stmt = select(Project)
            if filters:
                total_stmt = total_stmt.where(*filters)
                items_stmt = items_stmt.where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)
            items = (
                await session.scalars(items_stmt.order_by(Project.created_at.desc()).offset(page * size).limit(size))
            ).all()
            return list(items), total

    async def list_projects_all(self, search: str | None, exclude_codes: list[str]):
        filters = []
        if exclude_codes:
            filters.append(Project.project_code.notin_(exclude_codes))
        if search:
            term = f"%{search}%"
            filters.append(or_(Project.project_code.ilike(term), Project.project_name.ilike(term)))
        async with self.db.session() as session:
            stmt = select(Project)
            if filters:
                stmt = stmt.where(*filters)
            return list((await session.scalars(stmt.order_by(Project.project_name.asc()))).all())

    async def get_user_by_email(self, email: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def get_manager_project_codes(self, manager_user_id: int) -> list[str]:
        async with self.db.session() as session:
            stmt = (
                select(Project.project_code)
                .select_from(UserRole)
                .join(Role, UserRole.role_id == Role.id)
                .join(Project, UserRole.project_id == Project.id)
                .where(
                    UserRole.user_id == manager_user_id,
                    Role.name.in_(["MANAGER", "ROLE_MANAGER"]),
                )
            )
            project_codes = (await session.scalars(stmt)).all()
            return sorted({code for code in project_codes if code})

    async def get_projects_by_codes(self, project_codes: list[str]):
        if not project_codes:
            return []
        async with self.db.session() as session:
            return list((await session.scalars(select(Project).where(Project.project_code.in_(project_codes)))).all())

    async def get_active_allocations_for_project(self, project_code: str):
        async with self.db.session() as session:
            stmt = (
                select(Allocation)
                .join(Project, Allocation.project_id == Project.id)
                .where(Project.project_code == project_code, Allocation.is_active.is_(True))
                .options(selectinload(Allocation.user), selectinload(Allocation.project))
            )
            return list((await session.scalars(stmt)).all())

    async def get_user_role_for_project(self, user_id: int, project_code: str):
        async with self.db.session() as session:
            stmt = (
                select(UserRole)
                .join(Project, UserRole.project_id == Project.id)
                .where(UserRole.user_id == user_id, Project.project_code == project_code)
                .options(selectinload(UserRole.role), selectinload(UserRole.project))
            )
            return await session.scalar(stmt)

    async def get_active_allocations_for_user(self, user_id: int):
        async with self.db.session() as session:
            stmt = (
                select(Allocation)
                .where(Allocation.user_id == user_id, Allocation.is_active.is_(True))
                .options(selectinload(Allocation.project), selectinload(Allocation.user), selectinload(Allocation.override))
            )
            return list((await session.scalars(stmt)).all())
