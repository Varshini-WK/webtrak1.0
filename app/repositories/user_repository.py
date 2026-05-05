from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models.band import Band
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


class UserRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_by_email(self, email: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.email == email))

    async def get_by_id(self, user_id: int):
        async with self.db.session() as session:
            return await session.get(User, user_id)

    async def get_by_emp_id(self, emp_id: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.emp_id == emp_id))

    async def map_names_by_user_ids(self, user_ids: list[int]) -> dict[int, str]:
        """Return ``user_id -> display name`` for known users (omit missing ids)."""
        if not user_ids:
            return {}
        uniq = sorted(set(user_ids))
        async with self.db.session() as session:
            stmt = select(User.id, User.name).where(User.id.in_(uniq))
            rows = (await session.execute(stmt)).all()
        return {int(r[0]): ((r[1] or "").strip() or f"User {int(r[0])}") for r in rows}

    async def create_or_get_oauth_user(self, email: str, name: str):
        user = await self.get_by_email(email)
        if user:
            return user
        async with self.db.tx() as session:
            user = User(email=email, name=name)
            session.add(user)
            await session.flush()
            return user

    async def get_role_names_for_user(self, user_id: int) -> list[str]:
        async with self.db.session() as session:
            stmt = select(UserRole).where(UserRole.user_id == user_id).options(selectinload(UserRole.role))
            rows = (await session.scalars(stmt)).all()
            names = sorted({row.role.name for row in rows if row.role})
            return names if names else ["ROLE_EMPLOYEE"]

    async def list_all_users(self) -> list[User]:
        async with self.db.session() as session:
            return list((await session.scalars(select(User).order_by(User.id.asc()))).all())

    async def list_interns_with_doi_and_duration(self) -> list[User]:
        async with self.db.session() as session:
            stmt = select(User).where(
                User.user_type == "INTERN",
                User.doi.is_not(None),
                User.internship_duration.is_not(None),
                User.internship_duration > 0,
            )
            return list((await session.scalars(stmt)).all())

    async def list_users_by_role_names(self, role_names: list[str]) -> list[User]:
        if not role_names:
            return []
        async with self.db.session() as session:
            stmt = (
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(Role.name.in_(role_names))
                .order_by(User.id.asc())
            )
            rows = (await session.scalars(stmt)).all()
            dedup: dict[int, User] = {}
            for row in rows:
                dedup[row.id] = row
            return list(dedup.values())

    async def list_users_with_filters(
        self,
        *,
        search: str | None = None,
        band: str | None = None,
        user_type: str | None = None,
        statuses: list[str] | None = None,
    ) -> list[User]:
        async with self.db.session() as session:
            stmt = select(User).options(selectinload(User.band))
            filters = []
            if search and search.strip():
                like = f"%{search.strip()}%"
                filters.append(or_(User.name.ilike(like), User.email.ilike(like), User.emp_id.ilike(like)))
            if band and band.strip():
                band_value = band.strip()
                if band_value.isdigit():
                    filters.append(User.band_id == int(band_value))
                else:
                    stmt = stmt.join(Band, User.band_id == Band.id, isouter=True)
                    filters.append(Band.name.ilike(f"%{band_value}%"))
            if user_type and user_type.strip():
                filters.append(User.user_type == user_type.strip().upper())
            if statuses:
                filters.append(User.status.in_(statuses))
            if filters:
                stmt = stmt.where(*filters)
            rows = (await session.scalars(stmt.order_by(User.id.asc()))).all()
            return list(rows)
