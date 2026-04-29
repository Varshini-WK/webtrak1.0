from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webknot_value import WebknotValue


class WebknotValueRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_id(self, row_id: int) -> WebknotValue | None:
        async with self.db.session() as session:
            return await session.get(WebknotValue, row_id)

    async def list_paginated(self, limit: int, offset: int, active_only: bool | None) -> tuple[list[WebknotValue], int]:
        async with self.db.session() as session:
            base = select(WebknotValue)
            count_stmt = select(func.count()).select_from(WebknotValue)
            if active_only is True:
                base = base.where(WebknotValue.active.is_(True))
                count_stmt = select(func.count()).select_from(WebknotValue).where(WebknotValue.active.is_(True))
            total = int((await session.scalar(count_stmt)) or 0)
            rows = (
                await session.scalars(base.order_by(WebknotValue.id.asc()).offset(offset).limit(limit))
            ).all()
            return list(rows), total

    async def create(self, data: dict, client: AsyncSession | None = None) -> WebknotValue:
        if client is not None:
            obj = WebknotValue(**data)
            client.add(obj)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = WebknotValue(**data)
            session.add(obj)
            await session.flush()
            return obj

    async def update(self, row_id: int, data: dict, client: AsyncSession | None = None) -> WebknotValue | None:
        if client is not None:
            obj = await client.get(WebknotValue, row_id)
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            await client.flush()
            return obj
        async with self.db.tx() as session:
            obj = await session.get(WebknotValue, row_id)
            if not obj:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            await session.flush()
            return obj

    async def delete(self, row_id: int, client: AsyncSession | None = None) -> bool:
        if client is not None:
            obj = await client.get(WebknotValue, row_id)
            if not obj:
                return False
            await client.delete(obj)
            await client.flush()
            return True
        async with self.db.tx() as session:
            obj = await session.get(WebknotValue, row_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.flush()
            return True
