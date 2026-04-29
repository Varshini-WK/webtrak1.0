from sqlalchemy import select

from app.models.designation import Designation


class DesignationRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def list_by_band_and_department(self, band_id: int, department: str) -> list[Designation]:
        async with self.db.session() as session:
            stmt = (
                select(Designation)
                .where(Designation.band_id == band_id, Designation.department == department)
                .order_by(Designation.id.asc())
            )
            return list((await session.scalars(stmt)).all())

    async def exists_by_band_department_and_name(self, band_id: int, department: str, name: str) -> bool:
        async with self.db.session() as session:
            stmt = (
                select(Designation.id)
                .where(
                    Designation.band_id == band_id,
                    Designation.department.ilike(department.strip()),
                    Designation.name.ilike(name.strip()),
                )
                .limit(1)
            )
            return (await session.scalar(stmt)) is not None
