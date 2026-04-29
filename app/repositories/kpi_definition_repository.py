from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kpi_definition import KpiDefinition


class KpiDefinitionRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_id(self, kpi_id: int) -> KpiDefinition | None:
        async with self.db.session() as session:
            return await session.get(KpiDefinition, kpi_id)

    async def exists_duplicate(
        self,
        band_id: int,
        department: str,
        designation: str,
        kpi_name: str,
        exclude_id: int | None = None,
    ) -> bool:
        async with self.db.session() as session:
            stmt = select(func.count()).select_from(KpiDefinition).where(
                KpiDefinition.band_id == band_id,
                KpiDefinition.department == department,
                KpiDefinition.designation == designation,
                KpiDefinition.kpi_name == kpi_name,
            )
            if exclude_id is not None:
                stmt = stmt.where(KpiDefinition.id != exclude_id)
            return int((await session.scalar(stmt)) or 0) > 0

    async def list_all(self) -> list[KpiDefinition]:
        async with self.db.session() as session:
            return list((await session.scalars(select(KpiDefinition).order_by(KpiDefinition.id.asc()))).all())

    async def list_paginated(self, limit: int, offset: int) -> tuple[list[KpiDefinition], int]:
        async with self.db.session() as session:
            total = int((await session.scalar(select(func.count()).select_from(KpiDefinition))) or 0)
            rows = (
                await session.scalars(
                    select(KpiDefinition).order_by(KpiDefinition.id.asc()).offset(offset).limit(limit)
                )
            ).all()
            return list(rows), total

    async def create(self, data: dict, client: AsyncSession | None = None) -> KpiDefinition:
        if client is not None:
            obj = KpiDefinition(**data)
            client.add(obj)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = KpiDefinition(**data)
            session.add(obj)
            await session.flush()
            return obj

    async def update(self, kpi_id: int, data: dict, client: AsyncSession | None = None) -> KpiDefinition | None:
        if client is not None:
            obj = await client.get(KpiDefinition, kpi_id)
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = await session.get(KpiDefinition, kpi_id)
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            await session.flush()
            return obj

    async def delete(self, kpi_id: int, client: AsyncSession | None = None) -> bool:
        if client is not None:
            obj = await client.get(KpiDefinition, kpi_id)
            if not obj:
                return False
            await client.delete(obj)
            await client.flush()
            return True
        async with self.db.tx() as session:
            obj = await session.get(KpiDefinition, kpi_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.flush()
            return True
