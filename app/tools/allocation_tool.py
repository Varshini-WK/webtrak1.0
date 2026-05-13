from app.schemas.allocation import (
    AllocationCreateRequest,
    AllocationListResponse,
    AllocationRoleItem,
    AllocationResponse,
    AllocationUpdateRequest,
    BenchEquivalentUsersResponse,
    ForecastAllocationResponse,
    UserAllocationItem,
)
from app.services.allocation_service import AllocationService


class AllocationTool:
    def __init__(self, db) -> None:
        self.service = AllocationService(db)

    async def add_allocation(self, payload: AllocationCreateRequest, *, actor_roles: set[str]) -> AllocationResponse:
        return await self.service.add_allocation(payload, actor_roles=actor_roles)

    async def update_allocation(
        self,
        allocation_id: int,
        payload: AllocationUpdateRequest,
        *,
        actor_roles: set[str],
    ) -> AllocationResponse:
        return await self.service.update_allocation(allocation_id, payload, actor_roles=actor_roles)

    async def delete_allocation(self, allocation_id: int, *, actor_roles: set[str]) -> AllocationResponse:
        return await self.service.delete_allocation(allocation_id, actor_roles=actor_roles)

    async def list_allocations(
        self,
        *,
        project_code: str | None,
        user_email: str | None,
        search: str | None,
        page: int,
        size: int,
        view: str | None,
    ) -> AllocationListResponse:
        return await self.service.list_allocations(
            project_code=project_code,
            user_email=user_email,
            search=search,
            page=page,
            size=size,
            view=view,
        )

    async def list_bench_equivalent_users(
        self,
        *,
        search: str | None,
        page: int,
        size: int,
    ) -> BenchEquivalentUsersResponse:
        return await self.service.list_bench_equivalent_users(search=search, page=page, size=size)

    async def forecast(
        self,
        *,
        days: int,
        project_code: str | None,
        search: str | None,
        page: int,
        size: int,
    ) -> ForecastAllocationResponse:
        return await self.service.forecast(
            days=days,
            project_code=project_code,
            search=search,
            page=page,
            size=size,
        )

    async def list_my_allocations(self, email: str) -> list[UserAllocationItem]:
        return await self.service.list_my_allocations(email)

    async def import_batch_excel(self, content: bytes, *, actor_roles: set[str]) -> dict[str, int | str]:
        return await self.service.import_batch_excel(content, actor_roles=actor_roles)

    async def list_allocation_roles(self, search: str | None) -> list[AllocationRoleItem]:
        return await self.service.list_allocation_roles(search=search)
