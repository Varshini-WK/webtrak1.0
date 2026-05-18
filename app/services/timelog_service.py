from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import BytesIO, StringIO

from fastapi import HTTPException, status
from openpyxl import Workbook

from app.api.access import has_all_roles
from app.repositories.allocation_repository import AllocationRepository
from app.repositories.timelog_repository import TimeLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.timelog import (
    TimeLogCreateRequest,
    TimeLogListResponse,
    TimeLogResponse,
    TimeLogStatusBatchRequest,
    TimeLogStatusUpdateRequest,
    TimeLogUpdateRequest,
)


_HR_ADMIN_ROLES = frozenset({"ROLE_HR", "ROLE_ADMIN"})


def _normalize_roles(roles: set[str]) -> set[str]:
    out = set()
    for role in roles:
        r = role.strip().upper()
        if not r.startswith("ROLE_"):
            r = f"ROLE_{r}"
        out.add(r)
    return out


def _http(code: int, err_code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(status_code=code, detail={"code": err_code, "message": message, "details": details or {}})


class TimeLogService:
    def __init__(self, db) -> None:
        self.repo = TimeLogRepository(db)
        self.alloc_repo = AllocationRepository(db)
        self.user_repo = UserRepository(db)

    async def _actor_user(self, actor_email: str):
        user = await self.repo.get_user_by_email(actor_email)
        if not user:
            raise _http(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Actor user not found")
        return user

    async def _employee_has_hr_role(self, employee_email: str) -> bool:
        user = await self.repo.get_user_by_email(employee_email.strip().lower())
        if not user:
            return False
        names = await self.user_repo.get_role_names_for_user(int(user.id))
        return "ROLE_HR" in _normalize_roles(set(names))

    @staticmethod
    def _can_view_hr_employee_timelogs(actor_roles: set[str]) -> bool:
        return has_all_roles(_normalize_roles(actor_roles), _HR_ADMIN_ROLES)

    async def _resolve_view_scope(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        employee_email: str,
    ) -> list[str] | None:
        """Return manager project-code filter, or None when all projects for the employee are visible."""
        actor = actor_email.strip().lower()
        target = employee_email.strip().lower()
        roles = _normalize_roles(actor_roles)

        if actor == target:
            return None

        if await self._employee_has_hr_role(target):
            if not self._can_view_hr_employee_timelogs(roles):
                raise _http(
                    status.HTTP_403_FORBIDDEN,
                    "INSUFFICIENT_ROLE",
                    "HR employee timelogs require both HR and Admin roles to view",
                )
            return None

        if roles.intersection({"ROLE_HR", "ROLE_ADMIN"}):
            return None

        if "ROLE_MANAGER" in roles:
            manager = await self._actor_user(actor_email)
            return await self.repo.get_manager_project_codes(manager.id)

        raise _http(status.HTTP_403_FORBIDDEN, "INSUFFICIENT_ROLE", "Unauthorized user")

    async def _filter_export_rows_for_hr_visibility(self, rows: list, actor_roles: set[str]) -> list:
        if self._can_view_hr_employee_timelogs(actor_roles):
            return rows
        out: list = []
        hr_cache: dict[str, bool] = {}
        for row in rows:
            email = str(row.employeeEmail).strip().lower()
            if email not in hr_cache:
                hr_cache[email] = await self._employee_has_hr_role(email)
            if not hr_cache[email]:
                out.append(row)
        return out

    async def submit(self, actor_email: str, payload: TimeLogCreateRequest) -> TimeLogResponse:
        user = await self._actor_user(actor_email)
        code = payload.project_code.strip().upper()
        if code in {"BENCH", "GLOBAL"}:
            raise _http(status.HTTP_400_BAD_REQUEST, "INVALID_PROJECT", "Cannot submit timelog for system projects")
        if not await self.repo.project_exists(code):
            raise _http(status.HTTP_404_NOT_FOUND, "PROJECT_NOT_FOUND", "Project not found", {"project_code": code})
        row = await self.repo.create_timelog(
            {
                "userId": user.id,
                "employeeEmail": user.email,
                "projectCode": code,
                "logDate": payload.log_date,
                "hours": payload.hours,
                "description": payload.description,
                "status": "SUBMITTED",
                "createdAt": datetime.now(UTC).replace(tzinfo=None),
                "updatedAt": datetime.now(UTC).replace(tzinfo=None),
            }
        )
        return TimeLogResponse.from_record(row)

    async def list_my_logs(self, actor_email: str, page: int, size: int) -> TimeLogListResponse:
        items, total = await self.repo.list_employee_timelogs(actor_email, page, size)
        return TimeLogListResponse(items=[TimeLogResponse.from_record(i) for i in items], total=total, page=page, size=size)

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
        target = employee_email.strip().lower()
        allowed_project_codes = await self._resolve_view_scope(
            actor_email=actor_email,
            actor_roles=actor_roles,
            employee_email=target,
        )

        items, total = await self.repo.list_employee_timelogs_by_date(
            target,
            log_date,
            page,
            size,
            allowed_project_codes=allowed_project_codes,
        )
        return TimeLogListResponse(items=[TimeLogResponse.from_record(i) for i in items], total=total, page=page, size=size)

    async def edit(self, actor_email: str, timelog_id: int, payload: TimeLogUpdateRequest) -> TimeLogResponse:
        row = await self.repo.get_by_id(timelog_id)
        if not row:
            raise _http(status.HTTP_404_NOT_FOUND, "TIMELOG_NOT_FOUND", "Time log not found", {"timelog_id": timelog_id})
        if row.employeeEmail.lower() != actor_email.lower():
            raise _http(status.HTTP_403_FORBIDDEN, "SCOPE_VIOLATION", "You can edit only your own timelog")
        if row.status == "APPROVED":
            raise _http(status.HTTP_409_CONFLICT, "INVALID_STATE", "Approved timelog cannot be edited")
        code = payload.project_code.strip().upper()
        if not await self.repo.project_exists(code):
            raise _http(status.HTTP_404_NOT_FOUND, "PROJECT_NOT_FOUND", "Project not found", {"project_code": code})
        updated = await self.repo.update_timelog(
            timelog_id,
            {
                "project_code": code,
                "log_date": payload.log_date,
                "hours": payload.hours,
                "description": payload.description,
                "status": "SUBMITTED",
                "manager_comment": None,
                "reviewed_by": None,
                "reviewed_at": None,
            },
        )
        return TimeLogResponse.from_record(updated)

    async def delete(self, actor_email: str, timelog_id: int) -> dict[str, str]:
        row = await self.repo.get_by_id(timelog_id)
        if not row:
            raise _http(status.HTTP_404_NOT_FOUND, "TIMELOG_NOT_FOUND", "Time log not found", {"timelog_id": timelog_id})
        if row.employeeEmail.lower() != actor_email.lower():
            raise _http(status.HTTP_403_FORBIDDEN, "SCOPE_VIOLATION", "You can delete only your own timelog")
        if row.status == "APPROVED":
            raise _http(status.HTTP_409_CONFLICT, "INVALID_STATE", "Approved timelog cannot be deleted")
        await self.repo.delete_timelog(timelog_id)
        return {"message": "Time log deleted"}

    async def update_entry_java(
        self,
        *,
        actor_email: str,
        timelog_id: int,
        description: str | None,
        logged_hours: int,
    ) -> TimeLogResponse:
        row = await self.repo.get_by_id(timelog_id)
        if not row:
            raise _http(status.HTTP_404_NOT_FOUND, "TIMELOG_NOT_FOUND", "Time log not found", {"timelog_id": timelog_id})
        if row.employeeEmail.lower() != actor_email.lower():
            raise _http(status.HTTP_403_FORBIDDEN, "SCOPE_VIOLATION", "You can edit only your own timelog")
        updated = await self.repo.update_timelog(
            timelog_id,
            {
                "hours": logged_hours,
                "description": description,
                "updated_at": datetime.now(UTC).replace(tzinfo=None),
            },
        )
        return TimeLogResponse.from_record(updated)

    async def _assert_manager_scope(
        self,
        actor_email: str,
        actor_roles: set[str],
        project_code: str,
        *,
        employee_email: str | None = None,
    ) -> None:
        roles = _normalize_roles(actor_roles)
        if employee_email and await self._employee_has_hr_role(employee_email):
            if not self._can_view_hr_employee_timelogs(roles):
                raise _http(
                    status.HTTP_403_FORBIDDEN,
                    "INSUFFICIENT_ROLE",
                    "HR employee timelogs require both HR and Admin roles to manage",
                )
            return
        if roles.intersection({"ROLE_HR", "ROLE_ADMIN"}):
            return
        if "ROLE_MANAGER" not in roles:
            raise _http(status.HTTP_403_FORBIDDEN, "INSUFFICIENT_ROLE", "Manager/HR/Admin role required")
        actor = await self._actor_user(actor_email)
        is_manager = await self.repo.is_manager_for_project(actor.id, project_code.strip().upper())
        if not is_manager:
            raise _http(
                status.HTTP_403_FORBIDDEN,
                "MANAGER_SCOPE_DENIED",
                "You are not manager for this project",
                {"project_code": project_code},
            )

    async def update_status_single(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        payload: TimeLogStatusUpdateRequest,
    ) -> TimeLogResponse:
        row = await self.repo.get_by_id(payload.timelog_id)
        if not row:
            raise _http(status.HTTP_404_NOT_FOUND, "TIMELOG_NOT_FOUND", "Time log not found", {"timelog_id": payload.timelog_id})
        await self._assert_manager_scope(
            actor_email, actor_roles, row.projectCode, employee_email=str(row.employeeEmail)
        )
        updated = await self.repo.update_status_single(payload.timelog_id, payload.status, payload.manager_comment, actor_email)
        return TimeLogResponse.from_record(updated)

    async def update_status_batch(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        payload: TimeLogStatusBatchRequest,
    ) -> dict[str, int | str]:
        code = payload.project_code.strip().upper()
        await self._assert_manager_scope(
            actor_email, actor_roles, code, employee_email=str(payload.employee_email)
        )
        rows = await self.repo.update_status_batch(
            employee_email=str(payload.employee_email).lower(),
            project_code=code,
            log_date=payload.log_date,
            status_value=payload.status,
            manager_comment=payload.manager_comment,
            actor_email=actor_email,
        )
        return {"message": "Batch status update complete", "updated_count": len(rows)}

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
        roles = _normalize_roles(actor_roles)
        if not roles.intersection({"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"}):
            raise _http(status.HTTP_403_FORBIDDEN, "INSUFFICIENT_ROLE", "Manager/HR/Admin role required")
        if project_code and not roles.intersection({"ROLE_HR", "ROLE_ADMIN"}):
            await self._assert_manager_scope(actor_email, actor_roles, project_code)
        if employee_email:
            await self._resolve_view_scope(
                actor_email=actor_email,
                actor_roles=actor_roles,
                employee_email=employee_email,
            )
        rows = await self.repo.export_logs(
            project_code=project_code.strip().upper() if project_code else None,
            employee_email=employee_email.lower() if employee_email else None,
            start_date=start_date,
            end_date=end_date,
        )
        rows = await self._filter_export_rows_for_hr_visibility(rows, actor_roles)
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "employee_email", "project_code", "log_date", "hours", "status", "description", "reviewed_by"])
        for row in rows:
            writer.writerow(
                [
                    row.id,
                    row.employeeEmail,
                    row.projectCode,
                    row.logDate.isoformat(),
                    row.hours,
                    row.status,
                    row.description or "",
                    row.reviewedBy or "",
                ]
            )
        return buffer.getvalue()

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
        roles = _normalize_roles(actor_roles)
        if not roles.intersection({"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"}):
            raise _http(status.HTTP_403_FORBIDDEN, "INSUFFICIENT_ROLE", "Manager/HR/Admin role required")
        if project_code and not roles.intersection({"ROLE_HR", "ROLE_ADMIN"}):
            await self._assert_manager_scope(actor_email, actor_roles, project_code)
        if employee_email:
            await self._resolve_view_scope(
                actor_email=actor_email,
                actor_roles=actor_roles,
                employee_email=employee_email,
            )
        rows = await self.repo.export_logs(
            project_code=project_code.strip().upper() if project_code else None,
            employee_email=employee_email.lower() if employee_email else None,
            start_date=start_date,
            end_date=end_date,
        )
        return await self._filter_export_rows_for_hr_visibility(rows, actor_roles)

    def build_time_logs_xlsx(self, rows: list) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "TimeLogs"
        sheet.append(["Logged Date", "Logged Hours", "Description"])
        for row in rows:
            sheet.append([row.logDate.isoformat(), float(row.logged_hours), row.description or ""])
        out = BytesIO()
        workbook.save(out)
        return out.getvalue()

    async def build_project_summary_xlsx(self, rows: list) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Project Time Logs"
        sheet.append(["Date", "Employee Email", "Project Code", "Allocated Hours", "Total Logged Hours"])

        grouped: dict[tuple[str, str, str], float] = {}
        user_ids: dict[tuple[str, str, str], int] = {}
        for row in rows:
            key = (row.logDate.isoformat(), row.employeeEmail, row.projectCode)
            grouped[key] = float(grouped.get(key, 0.0) + float(row.logged_hours))
            user_ids[key] = int(row.user_id)

        for (log_date, emp_email, project_code), total_hours in sorted(grouped.items(), key=lambda x: (x[0][1], x[0][0])):
            allocated_hours = 0.0
            uid = user_ids.get((log_date, emp_email, project_code))
            if uid is not None:
                allocs = await self.alloc_repo.get_all_for_user_project(uid, project_code)
                if allocs:
                    allocated_hours = float(allocs[0].allocated_hours or 0.0)
            sheet.append([log_date, emp_email, project_code, allocated_hours, total_hours])

        out = BytesIO()
        workbook.save(out)
        return out.getvalue()
