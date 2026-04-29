from datetime import date

from app.schemas.timelog import (
    TimeLogCreateRequest,
    TimeLogListResponse,
    TimeLogResponse,
    TimeLogStatusBatchRequest,
    TimeLogStatusUpdateRequest,
    TimeLogUpdateRequest,
)
from app.services.timelog_service import TimeLogService


class TimeLogTool:
    def __init__(self, db) -> None:
        self.service = TimeLogService(db)

    async def submit(self, actor_email: str, payload: TimeLogCreateRequest) -> TimeLogResponse:
        return await self.service.submit(actor_email, payload)

    async def list_my_logs(self, actor_email: str, page: int, size: int) -> TimeLogListResponse:
        return await self.service.list_my_logs(actor_email, page, size)

    async def list_logs_by_user_and_date(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        employee_email: str,
        log_date: date,
        page: int,
        size: int,
    ) -> TimeLogListResponse:
        return await self.service.list_logs_by_user_and_date(
            actor_email=actor_email,
            actor_roles=actor_roles,
            employee_email=employee_email,
            log_date=log_date,
            page=page,
            size=size,
        )

    async def edit(self, actor_email: str, timelog_id: int, payload: TimeLogUpdateRequest) -> TimeLogResponse:
        return await self.service.edit(actor_email, timelog_id, payload)

    async def delete(self, actor_email: str, timelog_id: int) -> dict[str, str]:
        return await self.service.delete(actor_email, timelog_id)

    async def update_entry_java(
        self,
        *,
        actor_email: str,
        timelog_id: int,
        description: str | None,
        logged_hours: int,
    ) -> TimeLogResponse:
        return await self.service.update_entry_java(
            actor_email=actor_email,
            timelog_id=timelog_id,
            description=description,
            logged_hours=logged_hours,
        )

    async def update_status_single(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        payload: TimeLogStatusUpdateRequest,
    ) -> TimeLogResponse:
        return await self.service.update_status_single(actor_email=actor_email, actor_roles=actor_roles, payload=payload)

    async def update_status_batch(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        payload: TimeLogStatusBatchRequest,
    ) -> dict[str, int | str]:
        return await self.service.update_status_batch(actor_email=actor_email, actor_roles=actor_roles, payload=payload)

    async def export_csv(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        project_code: str | None,
        employee_email: str | None,
        start_date: date,
        end_date: date,
    ) -> str:
        return await self.service.export_csv(
            actor_email=actor_email,
            actor_roles=actor_roles,
            project_code=project_code,
            employee_email=employee_email,
            start_date=start_date,
            end_date=end_date,
        )

    async def export_rows(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        project_code: str | None,
        employee_email: str | None,
        start_date: date,
        end_date: date,
    ) -> list:
        return await self.service.export_rows(
            actor_email=actor_email,
            actor_roles=actor_roles,
            project_code=project_code,
            employee_email=employee_email,
            start_date=start_date,
            end_date=end_date,
        )

    def build_time_logs_xlsx(self, rows: list) -> bytes:
        return self.service.build_time_logs_xlsx(rows)

    async def build_project_summary_xlsx(self, rows: list) -> bytes:
        return await self.service.build_project_summary_xlsx(rows)
