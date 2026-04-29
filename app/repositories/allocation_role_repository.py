from sqlalchemy import select

from app.models.allocation_role import AllocationRole


class AllocationRoleRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_name_case_insensitive(self, name: str) -> AllocationRole | None:
        async with self.db.session() as session:
            stmt = select(AllocationRole).where(AllocationRole.name.ilike(name.strip()))
            return await session.scalar(stmt)

    async def list_all(self, search: str | None = None) -> list[AllocationRole]:
        async with self.db.session() as session:
            stmt = select(AllocationRole)
            if search and search.strip():
                like = f"%{search.strip()}%"
                stmt = stmt.where(AllocationRole.name.ilike(like))
            stmt = stmt.order_by(AllocationRole.name.asc())
            return list((await session.scalars(stmt)).all())

