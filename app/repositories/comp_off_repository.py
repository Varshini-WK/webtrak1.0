from datetime import date

from sqlalchemy import func, select

from app.models.comp_off_approval import CompOffApproval
from app.models.comp_off_grant import CompOffGrant
from app.models.comp_off_usage import CompOffUsage


class CompOffRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create_approval(self, payload: dict, client=None) -> CompOffApproval:
        row = CompOffApproval(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def create_grant(self, payload: dict, client=None) -> CompOffGrant:
        row = CompOffGrant(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def create_usage(self, payload: dict, client=None) -> CompOffUsage:
        row = CompOffUsage(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_active_grants(self, user_id: int, as_of: date) -> list[CompOffGrant]:
        async with self.db.session() as session:
            stmt = (
                select(CompOffGrant)
                .where(
                    CompOffGrant.user_id == user_id,
                    CompOffGrant.status == "ACTIVE",
                    CompOffGrant.expiry_date >= as_of,
                    CompOffGrant.remaining_units > 0,
                )
                .order_by(CompOffGrant.expiry_date.asc(), CompOffGrant.id.asc())
            )
            return list((await session.scalars(stmt)).all())

    async def sum_available_units(self, user_id: int, as_of: date) -> float:
        async with self.db.session() as session:
            stmt = select(func.coalesce(func.sum(CompOffGrant.remaining_units), 0.0)).where(
                CompOffGrant.user_id == user_id,
                CompOffGrant.status == "ACTIVE",
                CompOffGrant.expiry_date >= as_of,
            )
            value = await session.scalar(stmt)
            return float(value or 0.0)
