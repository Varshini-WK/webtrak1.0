from sqlalchemy import func, select

from app.models.user_request_tracking import UserRequestTracking


class UserRequestTrackingRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create(self, payload: dict, client=None) -> UserRequestTracking:
        row = UserRequestTracking(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_by_request(self, user_request_id: int) -> list[UserRequestTracking]:
        async with self.db.session() as session:
            stmt = (
                select(UserRequestTracking)
                .where(UserRequestTracking.user_request_id == user_request_id)
                .order_by(UserRequestTracking.created_at.asc(), UserRequestTracking.id.asc())
            )
            return list((await session.scalars(stmt)).all())

    async def list_by_request_and_actioner(self, user_request_id: int, actioner_id: int) -> list[UserRequestTracking]:
        async with self.db.session() as session:
            stmt = (
                select(UserRequestTracking)
                .where(
                    UserRequestTracking.user_request_id == user_request_id,
                    UserRequestTracking.actioner_id == actioner_id,
                )
                .order_by(UserRequestTracking.created_at.desc(), UserRequestTracking.id.desc())
            )
            return list((await session.scalars(stmt)).all())

    async def list_by_request_and_actions(self, user_request_id: int, actions: list[str]) -> list[UserRequestTracking]:
        if not actions:
            return []
        async with self.db.session() as session:
            stmt = (
                select(UserRequestTracking)
                .where(
                    UserRequestTracking.user_request_id == user_request_id,
                    UserRequestTracking.action.in_(actions),
                )
                .order_by(UserRequestTracking.created_at.asc(), UserRequestTracking.id.asc())
            )
            return list((await session.scalars(stmt)).all())

    async def has_action_for_request_and_actioners(
        self,
        *,
        user_request_id: int,
        actions: list[str],
        actioner_ids: list[int],
    ) -> bool:
        if not actions or not actioner_ids:
            return False
        async with self.db.session() as session:
            stmt = (
                select(func.count())
                .select_from(UserRequestTracking)
                .where(
                    UserRequestTracking.user_request_id == user_request_id,
                    UserRequestTracking.action.in_(actions),
                    UserRequestTracking.actioner_id.in_(actioner_ids),
                )
            )
            return int((await session.scalar(stmt)) or 0) > 0
