from app.schemas.allocation_extension import (
    AllocationExtensionRequestListResponse,
    CreateAllocationExtensionRequest,
    UpdateAllocationExtensionStatusRequest,
)
from app.services.allocation_extension_request_service import AllocationExtensionRequestService


class AllocationExtensionTool:
    def __init__(self, db) -> None:
        self.service = AllocationExtensionRequestService(db)

    async def create_request(self, manager_email: str, payload: CreateAllocationExtensionRequest) -> int:
        return await self.service.create_request(manager_email, payload)

    async def list_for_hr(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        status_value: str | None,
    ) -> AllocationExtensionRequestListResponse:
        return await self.service.list_for_hr(page=page, size=size, search=search, status_value=status_value)

    async def list_for_manager(
        self,
        *,
        manager_email: str,
        page: int,
        size: int,
        search: str | None,
        project_code: str | None,
    ) -> AllocationExtensionRequestListResponse:
        return await self.service.list_for_manager(
            manager_email=manager_email,
            page=page,
            size=size,
            search=search,
            project_code=project_code,
        )

    async def update_status(self, hr_email: str, payload: UpdateAllocationExtensionStatusRequest) -> int:
        return await self.service.update_status(hr_email, payload)
