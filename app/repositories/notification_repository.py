from datetime import datetime

from sqlalchemy import delete, func, select

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create(self, payload: dict, client=None) -> Notification:
        row = Notification(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def create_many(self, payloads: list[dict], client=None) -> list[Notification]:
        rows = [Notification(**payload) for payload in payloads]
        if not rows:
            return []
        if client is not None:
            client.add_all(rows)
            await client.flush()
            return rows
        async with self.db.tx() as session:
            session.add_all(rows)
            await session.flush()
            return rows

    async def list_for_user(self, user_id: int, limit: int = 50) -> list[Notification]:
        async with self.db.session() as session:
            stmt = (
                select(Notification)
                .where(Notification.receiver_id == user_id)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .limit(limit)
            )
            return list((await session.scalars(stmt)).all())

    async def list_for_user_page(self, user_id: int, page: int, size: int) -> tuple[list[Notification], int]:
        async with self.db.session() as session:
            total_stmt = select(func.count()).select_from(Notification).where(Notification.receiver_id == user_id)
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                select(Notification)
                .where(Notification.receiver_id == user_id)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .offset(page * size)
                .limit(size)
            )
            rows = list((await session.scalars(stmt)).all())
            return rows, total

    async def get_for_receiver(self, notification_id: int, receiver_id: int):
        async with self.db.session() as session:
            stmt = select(Notification).where(Notification.id == notification_id, Notification.receiver_id == receiver_id)
            return await session.scalar(stmt)

    async def mark_read(self, notification_id: int, receiver_id: int, client=None):
        if client is not None:
            row = await client.scalar(
                select(Notification).where(Notification.id == notification_id, Notification.receiver_id == receiver_id)
            )
            if not row:
                return None
            row.is_read = True
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.scalar(
                select(Notification).where(Notification.id == notification_id, Notification.receiver_id == receiver_id)
            )
            if not row:
                return None
            row.is_read = True
            await session.flush()
            return row

    async def mark_all_read(self, receiver_id: int, client=None) -> int:
        if client is not None:
            rows = (
                await client.scalars(
                    select(Notification).where(Notification.receiver_id == receiver_id, Notification.is_read.is_(False))
                )
            ).all()
            for row in rows:
                row.is_read = True
            await client.flush()
            return len(rows)
        async with self.db.tx() as session:
            rows = (
                await session.scalars(
                    select(Notification).where(Notification.receiver_id == receiver_id, Notification.is_read.is_(False))
                )
            ).all()
            for row in rows:
                row.is_read = True
            await session.flush()
            return len(rows)

    async def delete_read_notifications(self, client=None) -> int:
        stmt = delete(Notification).where(Notification.is_read.is_(True))
        if client is not None:
            result = await client.execute(stmt)
            return int(result.rowcount or 0)
        async with self.db.tx() as session:
            result = await session.execute(stmt)
            return int(result.rowcount or 0)

    async def exists_for_sender_type_between(
        self,
        *,
        sender_id: int,
        notification_type: str,
        start_at: datetime,
        end_at: datetime,
    ) -> bool:
        async with self.db.session() as session:
            stmt = (
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.sender_id == sender_id,
                    Notification.type == notification_type,
                    Notification.created_at >= start_at,
                    Notification.created_at <= end_at,
                )
            )
            return int((await session.scalar(stmt)) or 0) > 0

    async def exists_for_receiver_sender_type_between(
        self,
        *,
        receiver_id: int,
        sender_id: int | None,
        notification_type: str,
        start_at: datetime,
        end_at: datetime,
    ) -> bool:
        async with self.db.session() as session:
            where = [
                Notification.receiver_id == receiver_id,
                Notification.type == notification_type,
                Notification.created_at >= start_at,
                Notification.created_at <= end_at,
            ]
            if sender_id is None:
                where.append(Notification.sender_id.is_(None))
            else:
                where.append(Notification.sender_id == sender_id)
            stmt = select(func.count()).select_from(Notification).where(*where)
            return int((await session.scalar(stmt)) or 0) > 0
