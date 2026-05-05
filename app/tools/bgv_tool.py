from app.schemas.bgv import BgvUpsertRequest
from app.services.bgv_service import BgvService


class BgvTool:
    def __init__(self, db) -> None:
        self.service = BgvService(db)

    async def upsert_record(self, *, actor_email: str, emp_id: str, payload: BgvUpsertRequest):
        return await self.service.upsert_record(actor_email=actor_email, emp_id=emp_id, payload=payload)

    async def get_record(self, *, emp_id: str):
        return await self.service.get_record(emp_id=emp_id)

    async def list_dashboard(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        overall_status: str | None,
        employment_status: str | None,
        reference_status: str | None,
    ):
        return await self.service.list_dashboard(
            page=page,
            size=size,
            search=search,
            overall_status=overall_status,
            employment_status=employment_status,
            reference_status=reference_status,
        )
