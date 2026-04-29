from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.submission_cycle import SubmissionCycle


class SubmissionCycleRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_id(self, cycle_id: int) -> SubmissionCycle | None:
        async with self.db.session() as session:
            return await session.get(SubmissionCycle, cycle_id)

    async def get_by_cycle_key_and_scope(self, cycle_key: str, scope: str) -> SubmissionCycle | None:
        async with self.db.session() as session:
            return await session.scalar(
                select(SubmissionCycle).where(
                    SubmissionCycle.cycle_key == cycle_key,
                    SubmissionCycle.scope == scope,
                )
            )

    async def exists_duplicate(self, cycle_key: str, scope: str, exclude_id: int | None = None) -> bool:
        async with self.db.session() as session:
            stmt = select(func.count()).select_from(SubmissionCycle).where(
                SubmissionCycle.cycle_key == cycle_key,
                SubmissionCycle.scope == scope,
            )
            if exclude_id is not None:
                stmt = stmt.where(SubmissionCycle.id != exclude_id)
            return int((await session.scalar(stmt)) or 0) > 0

    async def list_all(self) -> list[SubmissionCycle]:
        async with self.db.session() as session:
            return list((await session.scalars(select(SubmissionCycle).order_by(SubmissionCycle.id.asc()))).all())

    async def list_paginated(self, limit: int, offset: int) -> tuple[list[SubmissionCycle], int]:
        async with self.db.session() as session:
            total = int((await session.scalar(select(func.count()).select_from(SubmissionCycle))) or 0)
            rows = (
                await session.scalars(
                    select(SubmissionCycle).order_by(SubmissionCycle.id.asc()).offset(offset).limit(limit)
                )
            ).all()
            return list(rows), total

    async def create(self, data: dict, client: AsyncSession | None = None) -> SubmissionCycle:
        if client is not None:
            obj = SubmissionCycle(**data)
            client.add(obj)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = SubmissionCycle(**data)
            session.add(obj)
            await session.flush()
            return obj

    async def update(self, cycle_id: int, data: dict, client: AsyncSession | None = None) -> SubmissionCycle | None:
        if client is not None:
            obj = await client.get(SubmissionCycle, cycle_id)
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = await session.get(SubmissionCycle, cycle_id)
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            await session.flush()
            return obj

    async def delete(self, cycle_id: int, client: AsyncSession | None = None) -> bool:
        if client is not None:
            obj = await client.get(SubmissionCycle, cycle_id)
            if not obj:
                return False
            await client.delete(obj)
            await client.flush()
            return True
        async with self.db.tx() as session:
            obj = await session.get(SubmissionCycle, cycle_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.flush()
            return True
