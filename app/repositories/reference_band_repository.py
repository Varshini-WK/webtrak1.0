from sqlalchemy import func, or_, select

from app.models.band import Band


class ReferenceBandRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def list_for_selection(self, search: str | None) -> list[Band]:
        stmt = select(Band).order_by(Band.name.asc())
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(or_(Band.name.ilike(term), Band.stream.ilike(term)))
        async with self.db.session() as session:
            return list((await session.scalars(stmt)).all())
