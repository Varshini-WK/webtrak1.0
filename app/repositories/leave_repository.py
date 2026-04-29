from sqlalchemy import select

from app.models.leave_mapping import LeaveMapping


class LeaveRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create_mapping(
        self,
        user_id: int,
        year: int,
        month: int,
        primary_leave: float,
        secondary_leave: float,
        carry_forward: float = 0.0,
        client=None,
    ):
        if client is not None:
            row = LeaveMapping(
                user_id=user_id,
                year=year,
                month=month,
                primary_leave=primary_leave,
                secondary_leave=secondary_leave,
                carry_forward=carry_forward,
            )
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = LeaveMapping(
                user_id=user_id,
                year=year,
                month=month,
                primary_leave=primary_leave,
                secondary_leave=secondary_leave,
                carry_forward=carry_forward,
            )
            session.add(row)
            await session.flush()
            return row

    async def get_mapping(self, user_id: int, year: int, month: int, client=None):
        stmt = select(LeaveMapping).where(
            LeaveMapping.user_id == user_id,
            LeaveMapping.year == year,
            LeaveMapping.month == month,
        )
        if client is not None:
            return await client.scalar(stmt)
        async with self.db.session() as session:
            return await session.scalar(stmt)

    async def save_mapping(self, row: LeaveMapping, client=None):
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_mappings_for_year_month(self, year: int, month: int) -> list[LeaveMapping]:
        async with self.db.session() as session:
            stmt = select(LeaveMapping).where(LeaveMapping.year == year, LeaveMapping.month == month)
            return list((await session.scalars(stmt)).all())
