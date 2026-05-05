from datetime import date, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.user_request import UserRequest


class UserRequestRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create(self, payload: dict, client=None) -> UserRequest:
        row = UserRequest(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def get_by_id(self, request_id: int) -> UserRequest | None:
        async with self.db.session() as session:
            stmt = (
                select(UserRequest)
                .where(UserRequest.id == request_id)
                .options(selectinload(UserRequest.user), selectinload(UserRequest.trackings))
            )
            return await session.scalar(stmt)

    async def get_by_id_with_lock(self, request_id: int, client) -> UserRequest | None:
        stmt = (
            select(UserRequest)
            .where(UserRequest.id == request_id)
            .with_for_update()
            .options(selectinload(UserRequest.user), selectinload(UserRequest.trackings))
        )
        return await client.scalar(stmt)

    async def list_for_user_in_window(
        self,
        *,
        user_id: int,
        request_type: str,
        from_date: date,
        to_date: date,
    ) -> list[UserRequest]:
        async with self.db.session() as session:
            stmt = (
                select(UserRequest)
                .where(
                    UserRequest.user_id == user_id,
                    UserRequest.request_type == request_type,
                    UserRequest.deleted.is_(False),
                    UserRequest.request_from_date <= to_date,
                    UserRequest.request_to_date >= from_date,
                )
                .order_by(UserRequest.request_from_date.desc(), UserRequest.id.desc())
            )
            return list((await session.scalars(stmt)).all())

    async def list_for_users(
        self,
        *,
        user_ids: list[int],
        from_date: date,
        to_date: date,
        request_type: str,
        page: int,
        size: int,
    ):
        if not user_ids:
            return [], 0
        async with self.db.session() as session:
            filters = [
                UserRequest.user_id.in_(user_ids),
                UserRequest.request_type == request_type,
                UserRequest.deleted.is_(False),
                UserRequest.request_from_date <= to_date,
                UserRequest.request_to_date >= from_date,
            ]
            total_stmt = select(func.count()).select_from(UserRequest).where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                select(UserRequest)
                .where(*filters)
                .options(selectinload(UserRequest.user))
                .order_by(UserRequest.request_from_date.desc(), UserRequest.id.desc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(stmt)).all())
            return items, total

    async def list_hr_filtered(
        self,
        *,
        page: int,
        size: int,
        request_type: str | None = None,
        status: str | None = None,
        search: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        async with self.db.session() as session:
            filters = [UserRequest.deleted.is_(False)]
            if request_type:
                filters.append(UserRequest.request_type == request_type)
            if status:
                filters.append(UserRequest.status == status)
            if from_date:
                filters.append(UserRequest.request_from_date >= from_date)
            if to_date:
                filters.append(UserRequest.request_to_date <= to_date)

            base = select(UserRequest).join(User, UserRequest.user_id == User.id)
            if search and search.strip():
                term = f"%{search.strip()}%"
                filters.append(or_(User.name.ilike(term), User.email.ilike(term), UserRequest.comments.ilike(term)))

            total_stmt = select(func.count()).select_from(UserRequest).join(User, UserRequest.user_id == User.id).where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)

            stmt = (
                base.where(*filters)
                .options(selectinload(UserRequest.user))
                .order_by(UserRequest.created_at.desc())
                .offset(page * size)
                .limit(size)
            )
            items = list((await session.scalars(stmt)).all())
            return items, total

    async def list_for_manager_scope(
        self,
        *,
        manager_email: str,
        manager_user_id: int,
        request_type: str,
        page: int,
        size: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ):
        async with self.db.session() as session:
            filters = [
                UserRequest.deleted.is_(False),
                UserRequest.request_type == request_type,
                UserRequest.user_id != manager_user_id,
            ]
            if request_type == "COMP_OFF":
                filters.append(UserRequest.manager_comp_off_email == manager_email)
            if from_date:
                filters.append(UserRequest.request_from_date >= from_date)
            if to_date:
                filters.append(UserRequest.request_to_date <= to_date)
            total_stmt = select(func.count()).select_from(UserRequest).where(*filters)
            total = int((await session.scalar(total_stmt)) or 0)
            stmt = (
                select(UserRequest)
                .where(*filters)
                .options(selectinload(UserRequest.user), selectinload(UserRequest.trackings))
                .order_by(UserRequest.created_at.desc())
                .offset(page * size)
                .limit(size)
            )
            rows = list((await session.scalars(stmt)).all())
            if request_type != "COMP_OFF":
                return rows, total
            filtered = [
                row
                for row in rows
                if any(t.actioner_id == manager_user_id for t in row.trackings if t.action in {"INITIATED", "APPROVED", "REJECTED"})
            ]
            return filtered, total

    async def save(self, row: UserRequest, client=None) -> UserRequest:
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_pending_for_exact_day(self, *, day: date, request_types: list[str]) -> list[UserRequest]:
        if not request_types:
            return []
        async with self.db.session() as session:
            stmt = (
                select(UserRequest)
                .where(
                    UserRequest.deleted.is_(False),
                    UserRequest.status == "PENDING",
                    UserRequest.request_type.in_(request_types),
                    UserRequest.request_from_date == day,
                )
                .options(selectinload(UserRequest.user), selectinload(UserRequest.trackings))
                .order_by(UserRequest.id.asc())
            )
            return list((await session.scalars(stmt)).all())
