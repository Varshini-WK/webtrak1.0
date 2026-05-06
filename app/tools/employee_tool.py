from fastapi import UploadFile

from app.schemas.attrition import AttritionRecordResponse, AttritionUpsertRequest
from app.schemas.employee import (
    EmployeeProfileHrUpdate,
    EmployeeProfileResponse,
    OnboardListResponse,
    OnboardUserResponse,
    ProfileUpdateRequest,
    UserOnboardCreate,
    UserOnboardUpdate,
)
from app.services.employee_service import EmployeeService


class EmployeeTool:
    def __init__(self, db) -> None:
        self.service = EmployeeService(db)

    async def create_user_onboard(self, payload: UserOnboardCreate) -> OnboardUserResponse:
        return await self.service.create_user_onboard(payload)

    async def update_user_onboard(
        self,
        payload: UserOnboardUpdate,
        resume: UploadFile | None,
        reliving_letter: UploadFile | None,
        salary_slips: list[UploadFile] | None,
        certifications: list[UploadFile] | None,
        profile_photo: UploadFile | None,
        aadhaar: UploadFile | None,
        pan_card: UploadFile | None,
    ) -> OnboardUserResponse:
        return await self.service.update_user_onboard(
            payload=payload,
            resume=resume,
            reliving_letter=reliving_letter,
            salary_slips=salary_slips,
            certifications=certifications,
            profile_photo=profile_photo,
            aadhaar=aadhaar,
            pan_card=pan_card,
        )

    async def get_profile(self, email: str) -> EmployeeProfileResponse:
        return await self.service.get_profile_by_email(email)

    async def update_profile(
        self,
        email: str,
        payload: ProfileUpdateRequest,
        profile_pic: UploadFile | None,
    ) -> EmployeeProfileResponse:
        return await self.service.update_profile(email=email, payload=payload, profile_pic=profile_pic)

    async def get_employee_profile(self, emp_id: str) -> EmployeeProfileResponse:
        return await self.service.get_employee_profile(emp_id)

    async def update_employee_profile(self, emp_id: str, payload: EmployeeProfileHrUpdate) -> EmployeeProfileResponse:
        return await self.service.update_employee_profile(emp_id, payload)

    async def get_onboarded_users(
        self,
        page: int,
        size: int,
        search: str | None,
        user_type: str | None,
        onboarding_status: str | None,
    ) -> OnboardListResponse:
        return await self.service.get_onboarded_users(page, size, search, user_type, onboarding_status)

    async def import_leave_data(self, content: bytes) -> dict[str, int | str]:
        return await self.service.import_leave_data(content)

    async def import_user_data(self, content: bytes) -> dict[str, int | str]:
        return await self.service.import_user_data(content)

    async def bulk_upload_users(self, content: bytes) -> dict[str, int | str]:
        return await self.service.bulk_upload_users(content)

    async def import_allocations_legacy(self, content: bytes, actor_roles: set[str]) -> dict[str, int | str | list[str]]:
        return await self.service.import_allocations_legacy(content, actor_roles)

    async def offboard_employee(
        self,
        *,
        actor_email: str,
        emp_id: str,
        payload: AttritionUpsertRequest,
    ) -> AttritionRecordResponse:
        return await self.service.offboard_employee(actor_email=actor_email, emp_id=emp_id, payload=payload)
