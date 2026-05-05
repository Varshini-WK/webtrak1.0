from sqlalchemy import and_, or_, select

from app.models.background_verification import BackgroundVerification
from app.models.band import Band
from app.models.user import User


class BgvRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def get_user_by_emp_id(self, emp_id: str):
        async with self.db.session() as session:
            return await session.scalar(select(User).where(User.emp_id == emp_id))

    async def get_with_user_and_band(self, *, user_id: int):
        async with self.db.session() as session:
            stmt = (
                select(BackgroundVerification, User, Band)
                .join(User, User.id == BackgroundVerification.user_id)
                .outerjoin(Band, Band.id == User.band_id)
                .where(BackgroundVerification.user_id == user_id)
            )
            return (await session.execute(stmt)).first()

    async def upsert_for_user(self, *, user_id: int, actor_id: int, payload: dict):
        async with self.db.tx() as session:
            row = await session.scalar(select(BackgroundVerification).where(BackgroundVerification.user_id == user_id))
            if row is None:
                row = BackgroundVerification(user_id=user_id, created_by=actor_id, updated_by=actor_id, **payload)
                session.add(row)
            else:
                for k, v in payload.items():
                    setattr(row, k, v)
                row.updated_by = actor_id
            await session.flush()
            return row

    async def list_dashboard_rows(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        overall_status: str | None,
        employment_status: str | None,
        reference_status: str | None,
    ) -> tuple[list[tuple[BackgroundVerification, User]], int]:
        async with self.db.session() as session:
            stmt = select(BackgroundVerification, User).join(User, User.id == BackgroundVerification.user_id)
            filters = []
            if search and search.strip():
                term = f"%{search.strip()}%"
                filters.append(or_(User.name.ilike(term), User.emp_id.ilike(term), User.email.ilike(term), User.role.ilike(term)))
            if overall_status and overall_status.strip():
                filters.append(BackgroundVerification.overall_status == overall_status.strip().upper())
            if employment_status and employment_status.strip():
                filters.append(BackgroundVerification.employment_status == employment_status.strip().upper())
            if reference_status and reference_status.strip():
                filters.append(BackgroundVerification.reference_status == reference_status.strip().upper())
            if filters:
                stmt = stmt.where(and_(*filters))

            rows = list((await session.execute(stmt.order_by(User.name.asc(), User.id.asc()))).all())
            total = len(rows)
            return rows[page * size : page * size + size], total
