from __future__ import annotations

from fastapi import HTTPException, status

from app.models.allocation import Allocation
from app.domain.notification_types import NotificationType
from app.repositories.allocation_extension_request_repository import AllocationExtensionRequestRepository
from app.repositories.allocation_repository import AllocationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.allocation_extension import (
    AllocationExtensionRequestListResponse,
    AllocationExtensionRequestOut,
    CreateAllocationExtensionRequest,
    UpdateAllocationExtensionStatusRequest,
)
from app.services.notification_service import NotificationService


class AllocationExtensionRequestService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = AllocationExtensionRequestRepository(db)
        self.alloc_repo = AllocationRepository(db)
        self.user_repo = UserRepository(db)
        self.notification_service = NotificationService(db)

    def _to_out(self, row) -> AllocationExtensionRequestOut:
        alloc = row.allocation
        user = alloc.user if alloc else None
        project = alloc.project if alloc else None
        requester = row.requested_by
        return AllocationExtensionRequestOut(
            id=row.id,
            employee_name=user.name if user else "",
            employee_email=user.email if user else "",
            project_code=project.projectCode if project else "",
            project_name=project.projectName if project else "",
            current_end_date=row.current_end_date,
            requested_end_date=row.requested_end_date,
            reason=row.reason,
            requested_by_name=requester.name if requester else "",
            status=row.status,
            created_at=row.created_at,
        )

    async def create_request(self, manager_email: str, payload: CreateAllocationExtensionRequest) -> int:
        manager = await self.user_repo.get_by_email(manager_email.lower())
        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")

        employee = await self.user_repo.get_by_email(payload.user_email.lower())
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        allocation = await self.alloc_repo.find_active_by_user_and_project(employee.id, payload.project_code.strip().upper())
        if not allocation:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active allocation not found for employee/project")
        if not allocation.endDate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extension allowed only when current allocation has an end date",
            )
        if payload.requested_end_date <= allocation.endDate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requested end date must be after current end date")

        async with self.db.tx() as tx:
            row = await self.repo.create(
                {
                    "allocation_id": allocation.id,
                    "requested_by_id": manager.id,
                    "reason": payload.reason,
                    "current_end_date": allocation.endDate,
                    "requested_end_date": payload.requested_end_date,
                    "status": "PENDING",
                },
                client=tx,
            )
            hr_users = await self.user_repo.list_users_by_role_names(["ROLE_HR", "HR"])
            await self.notification_service.send_notifications(
                receiver_ids=[u.id for u in hr_users],
                sender_id=manager.id,
                notification_type=NotificationType.ALLOCATION_EXTENSION_REQUEST,
                title="Allocation Extension Request",
                message=f"{manager.name} requested extension for {employee.email} on {payload.project_code}",
                client=tx,
            )
            return row.id

    async def list_for_hr(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        status_value: str | None,
    ) -> AllocationExtensionRequestListResponse:
        items, total = await self.repo.list_for_hr(page=page, size=size, search=search, status=status_value)
        return AllocationExtensionRequestListResponse(
            current_page=page,
            total_pages=(total + size - 1) // size if size else 0,
            page_size=size,
            total_elements=total,
            data=[self._to_out(item) for item in items],
        )

    async def list_for_manager(
        self,
        *,
        manager_email: str,
        page: int,
        size: int,
        search: str | None,
        project_code: str | None,
    ) -> AllocationExtensionRequestListResponse:
        manager = await self.user_repo.get_by_email(manager_email.lower())
        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")
        items, total = await self.repo.list_for_manager(
            manager_user_id=manager.id,
            page=page,
            size=size,
            search=search,
            project_code=project_code,
        )
        return AllocationExtensionRequestListResponse(
            current_page=page,
            total_pages=(total + size - 1) // size if size else 0,
            page_size=size,
            total_elements=total,
            data=[self._to_out(item) for item in items],
        )

    async def update_status(self, hr_email: str, payload: UpdateAllocationExtensionStatusRequest) -> int:
        hr_user = await self.user_repo.get_by_email(hr_email.lower())
        if not hr_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found")
        row = await self.repo.get_by_id(payload.request_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension request not found")
        if row.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending requests can be updated")
        if payload.status not in {"APPROVED", "REJECTED"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status update")

        async with self.db.tx() as tx:
            locked_row = await self.repo.get_by_id_with_lock(row.id, tx)
            locked_row.status = payload.status
            if payload.status == "APPROVED":
                alloc = await tx.get(Allocation, locked_row.allocation_id)
                alloc.end_date = locked_row.requested_end_date
            await self.notification_service.send_notification(
                receiver_id=locked_row.requested_by_id,
                sender_id=hr_user.id,
                notification_type=(
                    NotificationType.ALLOCATION_EXTENSION_APPROVED
                    if payload.status == "APPROVED"
                    else NotificationType.ALLOCATION_EXTENSION_REJECTED
                ),
                title=f"Allocation Extension {payload.status.title()}",
                message=f"Request #{locked_row.id} was {payload.status.lower()}",
                client=tx,
            )
            return locked_row.id
