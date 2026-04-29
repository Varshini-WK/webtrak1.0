from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.models.allocation import Allocation
from app.models.allocation_extension_request import AllocationExtensionRequest
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


class AllocationExtensionRequestRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create(self, payload: dict, client=None) -> AllocationExtensionRequest:
        row = AllocationExtensionRequest(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def get_by_id(self, request_id: int) -> AllocationExtensionRequest | None:
        async with self.db.session() as session:
            stmt = (
                select(AllocationExtensionRequest)
                .where(AllocationExtensionRequest.id == request_id)
                .options(
                    selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.user),
                    selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.project),
                    selectinload(AllocationExtensionRequest.requested_by),
                )
            )
            return await session.scalar(stmt)

    async def get_by_id_with_lock(self, request_id: int, client) -> AllocationExtensionRequest | None:
        stmt = (
            select(AllocationExtensionRequest)
            .where(AllocationExtensionRequest.id == request_id)
            .with_for_update()
            .options(
                selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.user),
                selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.project),
                selectinload(AllocationExtensionRequest.requested_by),
            )
        )
        return await client.scalar(stmt)

    async def latest_for_allocation(self, allocation_id: int) -> AllocationExtensionRequest | None:
        async with self.db.session() as session:
            stmt = (
                select(AllocationExtensionRequest)
                .where(AllocationExtensionRequest.allocation_id == allocation_id)
                .order_by(AllocationExtensionRequest.created_at.desc(), AllocationExtensionRequest.id.desc())
                .limit(1)
            )
            return await session.scalar(stmt)

    async def list_for_hr(self, *, page: int, size: int, search: str | None, status: str | None):
        async with self.db.session() as session:
            filters = []
            if status:
                filters.append(AllocationExtensionRequest.status == status)
            if search and search.strip():
                term = f"%{search.strip()}%"
                filters.append(
                    or_(
                        User.name.ilike(term),
                        User.email.ilike(term),
                        Project.project_name.ilike(term),
                        Project.project_code.ilike(term),
                    )
                )

            base = (
                select(AllocationExtensionRequest)
                .join(Allocation, AllocationExtensionRequest.allocation_id == Allocation.id)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
            )
            total_stmt = (
                select(func.count())
                .select_from(AllocationExtensionRequest)
                .join(Allocation, AllocationExtensionRequest.allocation_id == Allocation.id)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
            )
            if filters:
                base = base.where(*filters)
                total_stmt = total_stmt.where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                base.options(
                    selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.user),
                    selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.project),
                    selectinload(AllocationExtensionRequest.requested_by),
                )
                .order_by(AllocationExtensionRequest.created_at.desc(), AllocationExtensionRequest.id.desc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(stmt)).all())
            return items, total

    async def list_for_manager(
        self,
        *,
        manager_user_id: int,
        page: int,
        size: int,
        search: str | None,
        project_code: str | None,
    ):
        async with self.db.session() as session:
            managed_project_ids = (
                await session.scalars(
                    select(UserRole.project_id)
                    .join(Role, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == manager_user_id, Role.name.in_(["MANAGER", "ROLE_MANAGER"]))
                )
            ).all()
            if not managed_project_ids:
                return [], 0

            filters = [Allocation.project_id.in_(managed_project_ids)]
            if project_code and project_code.strip():
                filters.append(Project.project_code == project_code.strip())
            if search and search.strip():
                term = f"%{search.strip()}%"
                filters.append(
                    or_(
                        User.name.ilike(term),
                        User.email.ilike(term),
                        Project.project_name.ilike(term),
                        Project.project_code.ilike(term),
                    )
                )

            total_stmt = (
                select(func.count())
                .select_from(AllocationExtensionRequest)
                .join(Allocation, AllocationExtensionRequest.allocation_id == Allocation.id)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
            )
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                select(AllocationExtensionRequest)
                .join(Allocation, AllocationExtensionRequest.allocation_id == Allocation.id)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(*filters)
                .options(
                    selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.user),
                    selectinload(AllocationExtensionRequest.allocation).selectinload(Allocation.project),
                    selectinload(AllocationExtensionRequest.requested_by),
                )
                .order_by(AllocationExtensionRequest.created_at.desc(), AllocationExtensionRequest.id.desc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(stmt)).all())
            return items, total

    async def save(self, row: AllocationExtensionRequest, client=None) -> AllocationExtensionRequest:
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row
