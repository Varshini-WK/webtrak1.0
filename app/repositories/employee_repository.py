from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.employee_status import EmployeeStatus
from app.models.allocation import Allocation
from app.models.band import Band
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def _map_user_write_keys(data: dict) -> dict:
    keymap = {
        "empId": "emp_id",
        "userType": "user_type",
        "phoneNumber": "phone_number",
        "workMode": "work_mode",
        "deliveryStatus": "delivery_status",
        "workLocationType": "work_location_type",
        "bandId": "band_id",
        "internshipDuration": "internship_duration",
    }
    return {keymap.get(k, k): v for k, v in data.items()}


class EmployeeRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_user_by_email(self, email: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def get_user_by_emp_id(self, emp_id: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.emp_id == emp_id))

    async def get_band(self, band_id: int):
        async with self.db.session() as session:
            return await session.scalar(select(Band).where(Band.id == band_id))

    async def create_user(self, data: dict, client: AsyncSession | None = None):
        payload = _map_user_write_keys(data)
        if client is not None:
            obj = User(**payload)
            client.add(obj)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = User(**payload)
            session.add(obj)
            await session.flush()
            return obj

    async def update_user(self, user_id: int, data: dict, client: AsyncSession | None = None):
        payload = _map_user_write_keys(data)
        if client is not None:
            obj = await client.get(User, user_id)
            for k, v in payload.items():
                setattr(obj, k, v)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = await session.get(User, user_id)
            for k, v in payload.items():
                setattr(obj, k, v)
            await session.flush()
            return obj

    async def get_or_create_role(self, role_name: str):
        async with self.db.tx() as session:
            role = await session.scalar(select(Role).where(Role.name == role_name))
            if role:
                return role
            role = Role(name=role_name)
            session.add(role)
            await session.flush()
            return role

    async def assign_role(self, user_id: int, role_id: int, project_code: str | None = "GLOBAL", client: AsyncSession | None = None):
        target_project_code = (project_code or "GLOBAL").strip().upper()
        if client is not None:
            project = await client.scalar(select(Project).where(Project.project_code == target_project_code))
            if not project:
                project = Project(project_code=target_project_code, project_name=target_project_code.title(), project_type="IN_HOUSE", is_active=True)
                client.add(project)
                await client.flush()
            row = UserRole(user_id=user_id, role_id=role_id, project_id=project.id)
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            project = await session.scalar(select(Project).where(Project.project_code == target_project_code))
            if not project:
                project = Project(project_code=target_project_code, project_name=target_project_code.title(), project_type="IN_HOUSE", is_active=True)
                session.add(project)
                await session.flush()
            row = UserRole(user_id=user_id, role_id=role_id, project_id=project.id)
            session.add(row)
            await session.flush()
            return row

    async def create_bench_allocation(self, user_id: int, role: str | None, start_date, client: AsyncSession | None = None):
        if client is not None:
            bench_project_id = await client.scalar(select(Project.id).where(Project.project_code == "BENCH"))
            row = Allocation(
                user_id=user_id,
                project_id=bench_project_id,
                role=role or "bench",
                allocated_hours=8,
                start_date=start_date,
                is_active=True,
            )
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            bench_project_id = await session.scalar(select(Project.id).where(Project.project_code == "BENCH"))
            row = Allocation(
                user_id=user_id,
                project_id=bench_project_id,
                role=role or "bench",
                allocated_hours=8,
                start_date=start_date,
                is_active=True,
            )
            session.add(row)
            await session.flush()
            return row

    async def list_onboard_users(
        self,
        page: int,
        size: int,
        search: str | None,
        user_type: str | None,
        onboarding_status: str | None,
    ) -> tuple[list, int]:
        filters = []
        if search:
            term = f"%{search}%"
            filters.append(or_(User.name.ilike(term), User.email.ilike(term), User.emp_id.ilike(term)))
        if user_type:
            filters.append(User.user_type == user_type)
        if onboarding_status:
            filters.append(User.status == ("ONBOARDING" if onboarding_status.upper() == "PENDING" else "ACTIVE"))

        async with self.db.session() as session:
            total_stmt = select(func.count()).select_from(User)
            items_stmt = select(User)
            if filters:
                total_stmt = total_stmt.where(*filters)
                items_stmt = items_stmt.where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)
            items = (
                await session.scalars(items_stmt.offset(page * size).limit(size).order_by(User.id.asc()))
            ).all()
            return list(items), total

    async def list_recent_invited_users(self, limit: int = 6) -> list:
        stmt = (
            select(User)
            .where(User.status == EmployeeStatus.INVITED.value)
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        async with self.db.session() as session:
            return list((await session.scalars(stmt)).all())
