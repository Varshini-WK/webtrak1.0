from datetime import date

from app.schemas.user_request import (
    UserRequestCreate,
    UserRequestDelete,
    UserRequestListResponse,
    UserRequestStatusUpdate,
    UserRequestUpdate,
)
from app.services.user_request_service import UserRequestService


class UserRequestTool:
    def __init__(self, db) -> None:
        self.service = UserRequestService(db)

    async def create_request(self, actor_email: str, payload: UserRequestCreate) -> int:
        return await self.service.create_request(actor_email, payload)

    async def list_requests(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        from_date: date,
        to_date: date,
        request_type: str,
        page: int,
        size: int,
        emp_emails: list[str] | None = None,
    ) -> UserRequestListResponse:
        return await self.service.list_requests(
            actor_email=actor_email,
            actor_roles=actor_roles,
            from_date=from_date,
            to_date=to_date,
            request_type=request_type,
            page=page,
            size=size,
            emp_emails=emp_emails,
        )

    async def update_status(self, actor_email: str, actor_roles: set[str], payload: UserRequestStatusUpdate) -> int:
        return await self.service.update_status(actor_email, actor_roles, payload)

    async def update_request(self, actor_email: str, payload: UserRequestUpdate) -> int:
        return await self.service.update_request(actor_email, payload)

    async def delete_request(self, actor_email: str, payload: UserRequestDelete) -> str:
        return await self.service.delete_request(actor_email, payload.user_request_id)
