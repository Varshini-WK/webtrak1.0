from fastapi import HTTPException, status

from app.repositories.bgv_repository import BgvRepository
from app.repositories.user_repository import UserRepository
from app.schemas.bgv import BgvDashboardItem, BgvDashboardPage, BgvRecordResponse, BgvUpsertRequest


class BgvService:
    def __init__(self, db) -> None:
        self.bgv_repo = BgvRepository(db)
        self.user_repo = UserRepository(db)

    async def upsert_record(self, *, actor_email: str, emp_id: str, payload: BgvUpsertRequest) -> BgvRecordResponse:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor not found")
        user = await self.bgv_repo.get_user_by_emp_id(emp_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        normalized = {
            "consent_form_signed": payload.consent_form_signed,
            "identity": payload.identity,
            "employment_status": payload.employment_status.upper(),
            "reference_status": payload.reference_status.upper(),
            "mail_id_verified": str(payload.mail_id_verified) if payload.mail_id_verified else None,
            "onboarding_form_status": payload.onboarding_form_status.upper(),
            "overall_status": payload.overall_status.upper(),
            "remarks": payload.remarks,
        }
        await self.bgv_repo.upsert_for_user(user_id=int(user.id), actor_id=int(actor.id), payload=normalized)
        return await self.get_record(emp_id=emp_id)

    async def get_record(self, *, emp_id: str) -> BgvRecordResponse:
        user = await self.bgv_repo.get_user_by_emp_id(emp_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        row = await self.bgv_repo.get_with_user_and_band(user_id=int(user.id))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BGV record not found")
        bgv, db_user, band = row
        return BgvRecordResponse(
            employee_id=db_user.emp_id,
            name=db_user.name,
            role=db_user.role,
            level=(band.name if band else None),
            mail_id=db_user.email,
            consent_form_signed=bool(bgv.consent_form_signed),
            identity=bgv.identity,
            employment_status=bgv.employment_status,
            reference_status=bgv.reference_status,
            mail_id_verified=bgv.mail_id_verified,
            onboarding_form_status=bgv.onboarding_form_status,
            overall_status=bgv.overall_status,
            remarks=bgv.remarks,
        )

    async def list_dashboard(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        overall_status: str | None,
        employment_status: str | None,
        reference_status: str | None,
    ) -> BgvDashboardPage:
        rows, total = await self.bgv_repo.list_dashboard_rows(
            page=page,
            size=size,
            search=search,
            overall_status=overall_status,
            employment_status=employment_status,
            reference_status=reference_status,
        )
        items = [
            BgvDashboardItem(
                employee=user.name,
                role=user.role,
                consent=bool(bgv.consent_form_signed),
                identity=bgv.identity,
                employment=bgv.employment_status,
                overall_status=bgv.overall_status,
            )
            for bgv, user in rows
        ]
        total_page = 0 if total == 0 else (total + size - 1) // size
        return BgvDashboardPage(
            current_page=page,
            total_page=total_page,
            page_size=size,
            total_element=total,
            data=items,
        )
