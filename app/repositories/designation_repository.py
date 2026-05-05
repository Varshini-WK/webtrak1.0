from sqlalchemy import func, select

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

    async def list_unique_departments(self) -> list[str]:
        async with self.db.session() as session:
            stmt = (
                select(func.distinct(func.trim(Designation.department)))
                .where(Designation.department.is_not(None), func.trim(Designation.department) != "")
                .order_by(func.trim(Designation.department).asc())
            )
            rows = (await session.scalars(stmt)).all()
            return [str(row) for row in rows if row is not None]
