from __future__ import annotations

from io import BytesIO
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select

from app.domain.allocation_rules import (
    MAX_ALLOCATION_HOURS_PER_DAY,
    AllocationRuleError,
    AllocationType,
    BENCH_PROJECT_CODE,
    assert_new_allocation_fits_daily_cap,
    as_date,
    open_end_effective_date,
    validate_allocated_hours,
    validate_allocation_type_for_project,
    validate_date_window,
    validate_locked_in_date,
    validate_staffing_project_allocation_type,
)
from app.domain.notification_types import NotificationType
from app.repositories.allocation_role_repository import AllocationRoleRepository
from app.repositories.allocation_repository import AllocationRepository
from app.repositories.employee_repository import EmployeeRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.project import Project
from app.schemas.allocation import (
    AllocationCreateRequest,
    AllocationListResponse,
    AllocationResponse,
    AllocationUpdateRequest,
    ForecastAllocationResponse,
    AllocationRoleItem,
    UserAllocationItem,
)
from app.services.notification_service import NotificationService

MANAGER_ALLOCATION_ROLES = frozenset({"PM", "DM", "AM"})


def _normalize_actor_roles(actor_roles: set[str]) -> set[str]:
    out: set[str] = set()
    for r in actor_roles:
        x = r.strip().upper()
        if not x.startswith("ROLE_"):
            x = f"ROLE_{x}"
        out.add(x)
    return out


def _day_start_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _to_db_allocation_type(t: AllocationType | str) -> str:
    if isinstance(t, AllocationType):
        return t.value
    return AllocationType(t).value


def _domain_allocation_type(row) -> AllocationType:
    raw = getattr(row, "allocationType", None)
    if raw is None:
        return AllocationType.DEPLOYABLE
    v = raw.value if hasattr(raw, "value") else str(raw)
    return AllocationType(v)


class AllocationService:
    def __init__(self, db) -> None:
        self.db = db
        self.alloc_repo = AllocationRepository(db)
        self.alloc_role_repo = AllocationRoleRepository(db)
        self.project_repo = ProjectRepository(db)
        self.user_repo = UserRepository(db)
        self.employee_repo = EmployeeRepository(db)
        self.notification_service = NotificationService(db)

    async def _normalize_allocation_role(self, role: str | None, project_code: str) -> str | None:
        if role is None:
            return None
        cleaned = role.strip()
        if not cleaned:
            return None
        if project_code.strip().upper() == BENCH_PROJECT_CODE:
            return cleaned
        matched = await self.alloc_role_repo.get_by_name_case_insensitive(cleaned)
        if not matched:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid allocation role. Use a value from allocation roles master.",
            )
        return matched.name

    @staticmethod
    def _rule_error_as_http(exc: AllocationRuleError) -> HTTPException:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    async def _assign_manager_role(self, user_id: int, project_code: str, client=None) -> None:
        role_row = await self.employee_repo.get_or_create_role("ROLE_MANAGER")
        project = await client.scalar(select(Project).where(Project.project_code == project_code))
        if not project:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Project does not exist: {project_code}")
        existing = await client.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_row.id,
                UserRole.project_id == project.id,
            )
        )
        if not existing:
            await self.employee_repo.assign_role(user_id, role_row.id, project_code=project_code, client=client)

    async def _unassign_manager_role(self, user_id: int, project_code: str, client=None) -> None:
        role_row = await client.scalar(select(Role).where(Role.name == "ROLE_MANAGER"))
        if not role_row:
            return
        project = await client.scalar(select(Project).where(Project.project_code == project_code))
        if not project:
            return
        row = await client.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_row.id,
                UserRole.project_id == project.id,
            )
        )
        if row:
            await client.delete(row)

    async def recompute_bench_for_user(self, user_id: int, bench_role: str = "bench", client=None) -> None:
        cap = open_end_effective_date()
        today = date.today()

        bench_rows = await self.alloc_repo.get_active_bench_for_user(user_id, client=client)
        for b in bench_rows:
            await self.alloc_repo.deactivate(b.id, today, client=client)

        non_bench = await self.alloc_repo.get_active_non_bench_for_user(user_id, client=client)
        if not non_bench:
            await self.alloc_repo.create(
                {
                    "userId": user_id,
                    "projectCode": BENCH_PROJECT_CODE,
                    "role": bench_role,
                    "allocatedHours": MAX_ALLOCATION_HOURS_PER_DAY,
                    "startDate": _day_start_utc(today),
                    "endDate": None,
                    "isActive": True,
                    "allocationType": "DEPLOYABLE",
                },
                client=client,
            )
            return

        start_scan = min(min(as_date(a.startDate) for a in non_bench if as_date(a.startDate)), today)
        pre_total: int | None = None
        seg_start = start_scan
        prev_d = start_scan
        new_benches: list[dict] = []

        d = start_scan
        while d <= cap:
            day_total = 0
            for a in non_bench:
                if not a.isActive:
                    continue
                s = as_date(a.startDate)
                if s is None:
                    continue
                e = as_date(a.endDate) if a.endDate else cap
                if s <= d <= e:
                    day_total += int(a.allocatedHours)

            if pre_total is None:
                seg_start = d
            elif day_total != pre_total:
                bench_h = MAX_ALLOCATION_HOURS_PER_DAY - pre_total
                seg_end = prev_d
                if bench_h > 0:
                    new_benches.append(
                        {
                            "userId": user_id,
                            "projectCode": BENCH_PROJECT_CODE,
                            "role": bench_role,
                            "allocatedHours": bench_h,
                            "startDate": _day_start_utc(seg_start),
                            "endDate": None if seg_end >= cap else _day_start_utc(seg_end),
                            "isActive": True,
                            "allocationType": "DEPLOYABLE",
                        }
                    )
                seg_start = d
            pre_total = day_total
            prev_d = d
            d += timedelta(days=1)

        if pre_total is not None:
            bench_h = MAX_ALLOCATION_HOURS_PER_DAY - pre_total
            seg_end = prev_d
            if bench_h > 0:
                new_benches.append(
                    {
                        "userId": user_id,
                        "projectCode": BENCH_PROJECT_CODE,
                        "role": bench_role,
                        "allocatedHours": bench_h,
                        "startDate": _day_start_utc(seg_start),
                        "endDate": None if seg_end >= cap else _day_start_utc(seg_end),
                        "isActive": True,
                        "allocationType": "DEPLOYABLE",
                    }
                )

        for data in new_benches:
            await self.alloc_repo.create(data, client=client)

    async def _write_new_allocation(
        self,
        *,
        user_id: int,
        project_code: str,
        payload: AllocationCreateRequest,
        client,
    ) -> object:
        role_str = await self._normalize_allocation_role(payload.role, project_code)
        row = await self.alloc_repo.create(
            {
                "userId": user_id,
                "projectCode": project_code,
                "role": role_str,
                "allocatedHours": payload.allocated_hours,
                "startDate": _day_start_utc(payload.start_date),
                "endDate": _day_start_utc(payload.end_date) if payload.end_date else None,
                "isActive": True,
                "allocationType": _to_db_allocation_type(payload.allocation_type),
                "lockedInDate": _day_start_utc(payload.locked_in_date) if payload.locked_in_date else None,
                "billingStatus": payload.billing_status,
                "workLocationType": payload.work_location_type,
            },
            client=client,
        )
        if payload.work_location_type:
            await self.employee_repo.update_user(
                user_id,
                {"workLocationType": payload.work_location_type},
                client=client,
            )
        if payload.is_manager:
            await self._assign_manager_role(user_id, project_code, client=client)
        await self.recompute_bench_for_user(user_id, bench_role=role_str or "bench", client=client)
        return row

    async def add_allocation(
        self,
        payload: AllocationCreateRequest,
        *,
        actor_roles: set[str],
    ) -> AllocationResponse:
        normalized_roles = _normalize_actor_roles(actor_roles)
        if "ROLE_HR" not in normalized_roles and "ROLE_ADMIN" not in normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only HR or Admin can create allocations")

        user = await self.user_repo.get_by_email(str(payload.employee_email).lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        project = await self.project_repo.get_by_code(payload.project_code)
        if not project:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Project does not exist: {payload.project_code}")

        try:
            pt = project.projectType.value if hasattr(project.projectType, "value") else str(project.projectType)
            validate_allocation_type_for_project(payload.allocation_type, pt)
            validate_staffing_project_allocation_type(payload.allocation_type, pt)
            validate_locked_in_date(
                payload.start_date,
                payload.end_date,
                payload.locked_in_date,
                payload.allocation_type,
            )
        except AllocationRuleError as e:
            raise self._rule_error_as_http(e) from e

        dup = await self.alloc_repo.find_active_by_user_and_project(user.id, project.projectCode)
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Allocation already exists, update the existing allocation",
            )

        existing_for_cap = await self.alloc_repo.get_active_non_bench_for_user(user.id)
        try:
            assert_new_allocation_fits_daily_cap(
                existing_for_cap,
                payload.start_date,
                payload.end_date,
                payload.allocated_hours,
            )
        except AllocationRuleError as e:
            raise self._rule_error_as_http(e) from e

        async with self.db.tx() as tx:
            row = await self._write_new_allocation(
                user_id=user.id,
                project_code=project.projectCode,
                payload=payload,
                client=tx,
            )

        refreshed = await self.alloc_repo.get_by_id(row.id)
        await self.notification_service.send_notification(
            receiver_id=user.id,
            sender_id=None,
            notification_type=NotificationType.PROJECT_ASSIGNMENT,
            title="Project Assignment",
            message=f"You have been assigned to project {project.projectCode}.",
        )
        return AllocationResponse.from_record(refreshed)

    async def update_allocation(
        self,
        allocation_id: int,
        payload: AllocationUpdateRequest,
        *,
        actor_roles: set[str],
    ) -> AllocationResponse:
        normalized_roles = _normalize_actor_roles(actor_roles)
        if "ROLE_HR" not in normalized_roles and "ROLE_ADMIN" not in normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only HR or Admin can update allocations")

        existing = await self.alloc_repo.get_by_id(allocation_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation not found")

        project_existing = await self.project_repo.get_by_code(existing.projectCode)
        new_type = payload.resolved_type(_domain_allocation_type(existing))
        if project_existing:
            try:
                existing_pt = (
                    project_existing.projectType.value
                    if hasattr(project_existing.projectType, "value")
                    else str(project_existing.projectType)
                )
                if new_type == AllocationType.STAFFING and existing_pt != "STAFFING":
                    raise AllocationRuleError("STAFFING allocation type can be used only for STAFFING projects")
                validate_staffing_project_allocation_type(new_type, existing_pt)
            except AllocationRuleError as e:
                raise self._rule_error_as_http(e) from e

        target_project = await self.project_repo.get_by_code(payload.project_code)
        if not target_project:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Project does not exist: {payload.project_code}")

        start = date.today()
        end = payload.resolved_end()
        try:
            tgt_pt = (
                target_project.projectType.value
                if hasattr(target_project.projectType, "value")
                else str(target_project.projectType)
            )
            validate_date_window(start, end)
            validate_allocated_hours(payload.allocated_hours)
            validate_allocation_type_for_project(new_type, tgt_pt)
            validate_staffing_project_allocation_type(new_type, tgt_pt)
            validate_locked_in_date(start, end, payload.locked_in_date, new_type)
        except AllocationRuleError as e:
            raise self._rule_error_as_http(e) from e

        user = await self.user_repo.get_by_email(str(payload.employee_email).lower())
        if not user or user.id != existing.userId:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee must match the existing allocation user")

        existing_for_cap = [
            a
            for a in await self.alloc_repo.get_active_non_bench_for_user(user.id)
            if a.id != existing.id
        ]
        try:
            assert_new_allocation_fits_daily_cap(
                existing_for_cap,
                start,
                end,
                payload.allocated_hours,
            )
        except AllocationRuleError as e:
            raise self._rule_error_as_http(e) from e

        create_payload = AllocationCreateRequest(
            employee_email=payload.employee_email,
            project_code=payload.project_code,
            role=payload.role if payload.role is not None else existing.role,
            allocated_hours=payload.allocated_hours,
            start_date=start,
            end_date=end,
            allocation_type=new_type,
            locked_in_date=payload.locked_in_date,
            is_manager=payload.is_manager,
            billing_status=payload.billing_status if payload.billing_status is not None else existing.billingStatus,
            work_location_type=payload.work_location_type,
        )

        dup_other = await self.alloc_repo.find_active_by_user_and_project(user.id, target_project.projectCode)
        if dup_other and dup_other.id != existing.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Allocation already exists, update the existing allocation",
            )

        async with self.db.tx() as tx:
            await self.alloc_repo.deactivate(existing.id, date.today(), client=tx)
            row = await self._write_new_allocation(
                user_id=user.id,
                project_code=target_project.projectCode,
                payload=create_payload,
                client=tx,
            )

        refreshed = await self.alloc_repo.get_by_id(row.id)
        return AllocationResponse.from_record(refreshed)

    async def list_allocation_roles(self, search: str | None) -> list[AllocationRoleItem]:
        rows = await self.alloc_role_repo.list_all(search=search)
        return [AllocationRoleItem.model_validate(row) for row in rows]

    async def delete_allocation(self, allocation_id: int, *, actor_roles: set[str]) -> AllocationResponse:
        normalized_roles = _normalize_actor_roles(actor_roles)
        if "ROLE_HR" not in normalized_roles and "ROLE_ADMIN" not in normalized_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only HR or Admin can delete allocations")

        row = await self.alloc_repo.get_by_id(allocation_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation not found")

        today = date.today()
        locked = as_date(row.lockedInDate) if row.lockedInDate else None
        if locked is not None and today < locked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a locked allocation before the locked-in date.",
            )

        role_val = (row.role or "").strip()
        async with self.db.tx() as tx:
            await self.alloc_repo.deactivate(row.id, today, client=tx)
            if role_val in MANAGER_ALLOCATION_ROLES:
                await self._unassign_manager_role(row.userId, row.projectCode, client=tx)
            await self.recompute_bench_for_user(row.userId, client=tx)

        updated = await self.alloc_repo.get_by_id(allocation_id)
        await self.notification_service.send_notification(
            receiver_id=row.userId,
            sender_id=None,
            notification_type=NotificationType.PROJECT_DEALLOCATION,
            title="Project Deallocation",
            message=f"You have been deallocated from project {row.projectCode}.",
        )
        return AllocationResponse.from_record(updated)

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
        user_id = None
        if user_email:
            u = await self.user_repo.get_by_email(user_email.strip().lower())
            if not u:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            user_id = u.id

        pc = project_code.strip().upper() if project_code else None
        if pc == BENCH_PROJECT_CODE and view and view.upper() == "CURRENT":
            items, total = await self.alloc_repo.find_current_bench_page(search=search, page=page, size=size)
        else:
            items, total = await self.alloc_repo.list_page(
                project_code=pc,
                user_id=user_id,
                search=search,
                page=page,
                size=size,
            )

        return AllocationListResponse(
            current_page=page,
            total_pages=(total + size - 1) // size if size else 0,
            page_size=size,
            total_elements=total,
            allocations=[AllocationResponse.from_record(a) for a in items],
        )

    async def forecast(
        self,
        *,
        days: int,
        project_code: str | None,
        search: str | None,
        page: int,
        size: int,
    ) -> ForecastAllocationResponse:
        if days < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="days must be at least 1")
        cutoff = date.today() + timedelta(days=days)
        pc = project_code.strip().upper() if project_code else None
        items, total = await self.alloc_repo.find_forecast_page(
            cutoff=cutoff,
            project_code=pc,
            search=search,
            page=page,
            size=size,
        )
        return ForecastAllocationResponse(
            current_page=page,
            total_pages=(total + size - 1) // size if size else 0,
            page_size=size,
            total_elements=total,
            allocations=[AllocationResponse.from_record(a) for a in items],
        )

    async def list_my_allocations(self, email: str) -> list[UserAllocationItem]:
        user = await self.user_repo.get_by_email(email.strip().lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        rows = await self.alloc_repo.get_active_for_user(user.id)
        out: list[UserAllocationItem] = []
        for a in rows:
            if a.projectCode == BENCH_PROJECT_CODE:
                continue
            proj = await self.project_repo.get_by_code(a.projectCode)
            project_name = proj.projectName if proj else a.projectCode
            manager_name = "N/A"
            async with self.db.session() as session:
                mgr_row = await session.scalar(
                    select(UserRole)
                    .join(Role, UserRole.role_id == Role.id)
                    .join(Project, UserRole.project_id == Project.id)
                    .where(
                        Project.project_code == a.projectCode,
                        Role.name.in_(["ROLE_MANAGER", "MANAGER"]),
                    )
                )
            if mgr_row:
                async with self.db.session() as session:
                    manager = await session.get(User, mgr_row.user_id)
                if manager:
                    manager_name = manager.name
            out.append(
                UserAllocationItem(
                    project_name=project_name,
                    manager_name=manager_name,
                    allocated_hours=int(a.allocatedHours),
                )
            )
        return out

    async def import_batch_excel(self, content: bytes, *, actor_roles: set[str]) -> dict[str, int | str]:
        normalized = _normalize_actor_roles(actor_roles)
        if "ROLE_ADMIN" not in normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin can run allocation batch import",
            )
        try:
            import openpyxl
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Batch import requires openpyxl; add it to dependencies.",
            ) from e

        wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = wb.active
        completed = 0
        errors: list[str] = []
        row_num = 1
        for row in sheet.iter_rows(min_row=2, values_only=True):
            row_num += 1
            if not row or all(v is None for v in row[:4]):
                continue
            try:
                project_cell, email_cell, role_cell, hours_cell = row[0], row[1], row[2], row[3]
                if project_cell is None or email_cell is None:
                    continue
                project_code = str(project_cell).strip().upper()
                email = str(email_cell).strip().lower()
                role = str(role_cell).strip() if role_cell is not None else "Employee"
                hours = int(float(hours_cell)) if hours_cell is not None else 8
                payload = AllocationCreateRequest(
                    employee_email=email,
                    project_code=project_code,
                    role=role,
                    allocated_hours=hours,
                    start_date=date.today(),
                    end_date=None,
                    allocation_type=AllocationType.DEPLOYABLE,
                )
                await self.add_allocation(payload, actor_roles=actor_roles)
                completed += 1
            except Exception as exc:
                errors.append(f"row {row_num}: {exc}")

        msg = f"Import complete — added {completed} allocations"
        if errors:
            msg += f"; {len(errors)} row(s) skipped"
        return {"completed": completed, "message": msg, "errors": errors[:50]}
