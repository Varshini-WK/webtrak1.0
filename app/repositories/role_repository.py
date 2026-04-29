from sqlalchemy import select

from app.models.role import Role
from app.models.project import Project
from app.models.user import User
from app.models.user_role import UserRole


class RoleRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_user_by_email(self, email: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def get_role_by_name(self, role_name: str):
        async with self.db.session() as session:
            return await session.scalar(select(Role).where(Role.name == role_name))

    async def create_role(self, role_name: str):
        async with self.db.tx() as session:
            role = Role(name=role_name)
            session.add(role)
            await session.flush()
            return role

    async def get_or_create_role(self, role_name: str):
        role = await self.get_role_by_name(role_name)
        if role:
            return role
        return await self.create_role(role_name)

    async def user_has_role(self, user_id: int, role_id: int) -> bool:
        async with self.db.session() as session:
            existing = await session.scalar(
                select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
            )
            return existing is not None

    async def assign_role(self, user_id: int, role_id: int, project_code: str = "GLOBAL"):
        async with self.db.tx() as session:
            project = await session.scalar(select(Project).where(Project.project_code == project_code))
            if not project:
                project = Project(project_code=project_code, project_name=project_code.title(), project_type="IN_HOUSE", is_active=True)
                session.add(project)
                await session.flush()
            row = UserRole(user_id=user_id, role_id=role_id, project_id=project.id)
            session.add(row)
            await session.flush()
            return row
