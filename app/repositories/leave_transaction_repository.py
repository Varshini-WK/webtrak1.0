from datetime import date

from sqlalchemy import and_, func, select

from app.models.leave_transaction import LeaveTransaction


class LeaveTransactionRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create_many(self, rows: list[dict], client=None) -> list[LeaveTransaction]:
        entities = [LeaveTransaction(**row) for row in rows]
        if client is not None:
            client.add_all(entities)
            await client.flush()
            return entities
        async with self.db.tx() as session:
            session.add_all(entities)
            await session.flush()
            return entities

    async def list_by_user_request(self, user_request_id: int, client=None) -> list[LeaveTransaction]:
        stmt = select(LeaveTransaction).where(LeaveTransaction.user_request_id == user_request_id)
        if client is not None:
            return list((await client.scalars(stmt)).all())
        async with self.db.session() as session:
            return list((await session.scalars(stmt)).all())

    async def list_by_user_and_date(self, user_id: int, for_date: date) -> list[LeaveTransaction]:
        async with self.db.session() as session:
            stmt = select(LeaveTransaction).where(LeaveTransaction.user_id == user_id, LeaveTransaction.for_date == for_date)
            return list((await session.scalars(stmt)).all())

    async def list_for_user_month(self, user_id: int, year: int, month: int) -> list[LeaveTransaction]:
        async with self.db.session() as session:
            stmt = select(LeaveTransaction).where(
                LeaveTransaction.user_id == user_id,
                and_(
                    LeaveTransaction.for_date >= date(year, month, 1),
                    LeaveTransaction.for_date < date(year + (month // 12), (month % 12) + 1, 1),
                ),
            )
            return list((await session.scalars(stmt)).all())

    async def list_deducts_for_user_ids_date_range(
        self, user_ids: list[int], from_date: date, to_date: date
    ) -> list[tuple[int, date, float]]:
        if not user_ids:
            return []
        async with self.db.session() as session:
            stmt = (
                select(LeaveTransaction.user_id, LeaveTransaction.for_date, LeaveTransaction.value)
                .where(
                    LeaveTransaction.user_id.in_(user_ids),
                    LeaveTransaction.for_date >= from_date,
                    LeaveTransaction.for_date <= to_date,
                    func.upper(LeaveTransaction.transaction_type) == "DEDUCT",
                )
                .order_by(LeaveTransaction.user_id.asc(), LeaveTransaction.for_date.asc())
            )
            rows = (await session.execute(stmt)).all()
        return [(int(r[0]), r[1], float(r[2] or 0.0)) for r in rows]
