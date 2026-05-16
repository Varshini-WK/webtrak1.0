from datetime import date

from fastapi import HTTPException, status

from app.domain.project_code import format_auto_project_code
from app.repositories.allocation_repository import AllocationRepository
from app.repositories.leave_transaction_repository import LeaveTransactionRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import (
    CreateProjectRequest,
    ManagerProjectsResponse,
    ManagerTeamOnLeaveMember,
    ManagerTeamOnLeaveProjectItem,
    ManagerTeamOnLeaveTodayResponse,
    ProjectCodeNameResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSimpleListResponse,
    ProjectTypeEnum,
    ProjectWithEmployeesResponse,
)


SYSTEM_PROJECT_CODES = {"BENCH", "GLOBAL", "TALENT_POOL"}


class ProjectService:
    def __init__(self, db) -> None:
        self.repo = ProjectRepository(db)
        self.alloc_repo = AllocationRepository(db)
        self.leave_tx_repo = LeaveTransactionRepository(db)
        self.user_repo = UserRepository(db)

    @staticmethod
    def _clean_project_code(project_code: str) -> str:
        cleaned = project_code.strip().upper()
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project code is required")
        return cleaned

    @staticmethod
    def _clean_project_name(project_name: str) -> str:
        cleaned = project_name.strip()
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name is required")
        return cleaned

    @staticmethod
    def _to_project_response(project) -> ProjectResponse:
        raw_pt = project.projectType
        if isinstance(raw_pt, ProjectTypeEnum):
            pt_enum = raw_pt
        else:
            pt_enum = ProjectTypeEnum(str(raw_pt))
        mgr = getattr(project, "account_manager", None)
        return ProjectResponse(
            project_code=project.projectCode,
            project_name=project.projectName,
            project_type=pt_enum,
            is_active=project.isActive,
            client_name=getattr(project, "client_name", None),
            account_manager_email=mgr.email if mgr else None,
            account_manager_name=mgr.name if mgr else None,
        )

    async def create_project(self, payload: CreateProjectRequest) -> ProjectResponse:
        project_name = self._clean_project_name(payload.project_name)
        client_name = self._clean_project_name(payload.client_name)

        account_manager = await self.repo.get_user_by_email(str(payload.account_manager_email).strip().lower())
        if not account_manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account manager employee not found for the given email",
            )

        raw_code = (payload.project_code or "").strip()
        if raw_code:
            project_code = self._clean_project_code(raw_code)
        else:
            seq_start = await self.repo.max_p_auto_sequence() + 1
            project_code = ""
            for seq in range(seq_start, seq_start + 200):
                candidate = format_auto_project_code(seq, client_name)
                if not await self.repo.get_by_code(candidate):
                    project_code = candidate
                    break
            if not project_code:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not allocate a unique project code",
                )

        if await self.repo.get_by_code(project_code):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project code already exists")
        if await self.repo.get_by_name_case_insensitive(project_name):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name already exists")

        created = await self.repo.create_project(
            {
                "projectCode": project_code,
                "projectName": project_name,
                "projectType": payload.project_type.value,
                "isActive": True,
                "clientName": client_name,
                "accountManagerUserId": account_manager.id,
            }
        )
        return self._to_project_response(created)

    async def bulk_create(self, payload: list[CreateProjectRequest]) -> list[ProjectResponse]:
        results: list[ProjectResponse] = []
        for item in payload:
            results.append(await self.create_project(item))
        return results

    async def get_project_by_code(self, project_code: str) -> ProjectResponse:
        cleaned_code = self._clean_project_code(project_code)
        project = await self.repo.get_by_code(cleaned_code)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return self._to_project_response(project)

    async def get_all_projects(self, page: int, size: int, search: str | None) -> ProjectListResponse:
        items, total = await self.repo.list_projects(page, size, search, sorted(SYSTEM_PROJECT_CODES))
        return ProjectListResponse(items=[self._to_project_response(item) for item in items], total=total, page=page, size=size)

    async def get_all_projects_without_pagination(self, search: str | None) -> ProjectSimpleListResponse:
        items = await self.repo.list_projects_all(search, sorted(SYSTEM_PROJECT_CODES))
        return ProjectSimpleListResponse(items=[self._to_project_response(item) for item in items], total=len(items))

    async def get_manager_projects(self, manager_email: str, include_roles: bool) -> ManagerProjectsResponse:
        manager = await self.repo.get_user_by_email(manager_email)
        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")

        project_codes = await self.repo.get_manager_project_codes(manager.id)
        projects = await self.repo.get_projects_by_codes(project_codes)
        project_by_code = {project.projectCode: project for project in projects}

        result_projects: list[ProjectWithEmployeesResponse] = []
        for code in project_codes:
            project = project_by_code.get(code)
            if not project or code in SYSTEM_PROJECT_CODES:
                continue

            allocations = await self.repo.get_active_allocations_for_project(code)
            employees: list[dict] = []
            for allocation in allocations:
                if not allocation.user or allocation.user.id == manager.id:
                    continue
                entry = {
                    "emp_id": allocation.user.empId,
                    "email": allocation.user.email,
                    "name": allocation.user.name,
                    "allocated_hours": allocation.allocatedHours,
                }
                if include_roles:
                    # For manager-projects-with-roles, expose allocation designation role
                    # (e.g. UI Developer) rather than auth role from user_roles.
                    entry["project_role"] = allocation.role
                employees.append(entry)

            result_projects.append(
                ProjectWithEmployeesResponse(
                    project_code=project.projectCode,
                    project_name=project.projectName,
                    project_type=project.projectType,
                    employees=employees,
                )
            )

        return ManagerProjectsResponse(manager_email=manager.email, manager_name=manager.name, projects=result_projects)

    async def get_manager_team_on_leave_today(
        self, manager_email: str, as_of_date: date | None = None
    ) -> ManagerTeamOnLeaveTodayResponse:
        ref = as_of_date or date.today()
        manager = await self.repo.get_user_by_email(manager_email)
        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")

        raw_codes = await self.repo.get_manager_project_codes(manager.id)
        project_codes = [c for c in raw_codes if c and c not in SYSTEM_PROJECT_CODES]
        if not project_codes:
            return ManagerTeamOnLeaveTodayResponse(
                as_of_date=ref,
                manager_email=manager.email,
                manager_name=manager.name,
                team_on_leave=[],
            )

        pairs = await self.alloc_repo.list_user_project_pairs_for_projects_on_date(project_codes, ref)
        user_projects: dict[int, set[str]] = {}
        for user_id, code in pairs:
            if user_id == manager.id:
                continue
            user_projects.setdefault(user_id, set()).add(code)

        candidate_ids = sorted(user_projects.keys())
        if not candidate_ids:
            return ManagerTeamOnLeaveTodayResponse(
                as_of_date=ref,
                manager_email=manager.email,
                manager_name=manager.name,
                team_on_leave=[],
            )

        deduct_rows = await self.leave_tx_repo.list_deducts_for_user_ids_date_range(candidate_ids, ref, ref)
        leave_sum: dict[int, float] = {}
        for uid, _d, val in deduct_rows:
            leave_sum[uid] = leave_sum.get(uid, 0.0) + val

        on_leave_ids = sorted(uid for uid in candidate_ids if leave_sum.get(uid, 0.0) > 0.0)
        if not on_leave_ids:
            return ManagerTeamOnLeaveTodayResponse(
                as_of_date=ref,
                manager_email=manager.email,
                manager_name=manager.name,
                team_on_leave=[],
            )

        projects = await self.repo.get_projects_by_codes(project_codes)
        name_by_code = {p.projectCode: p.projectName for p in projects}

        users = await self.user_repo.list_by_ids(on_leave_ids)
        user_by_id = {u.id: u for u in users}

        members: list[ManagerTeamOnLeaveMember] = []
        for uid in on_leave_ids:
            u = user_by_id.get(uid)
            if not u:
                continue
            codes = sorted(user_projects.get(uid, set()))
            proj_items = [
                ManagerTeamOnLeaveProjectItem(project_code=c, project_name=name_by_code.get(c, c)) for c in codes
            ]
            members.append(
                ManagerTeamOnLeaveMember(
                    user_id=uid,
                    emp_id=u.empId,
                    email=u.email,
                    name=u.name,
                    leave_units_today=round(leave_sum.get(uid, 0.0), 4),
                    projects=proj_items,
                )
            )
        members.sort(key=lambda m: (m.name.lower(), m.user_id))

        return ManagerTeamOnLeaveTodayResponse(
            as_of_date=ref,
            manager_email=manager.email,
            manager_name=manager.name,
            team_on_leave=members,
        )

    async def get_project_codes_for_user(self, email: str) -> list[ProjectCodeNameResponse]:
        user = await self.repo.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        allocations = await self.repo.get_active_allocations_for_user(user.id)
        latest_by_code: dict[str, object] = {}
        for row in allocations:
            code = row.projectCode
            if not code or code in SYSTEM_PROJECT_CODES:
                continue
            existing = latest_by_code.get(code)
            if existing is None:
                latest_by_code[code] = row
                continue
            if getattr(row, "startDate", None) and getattr(existing, "startDate", None) and row.startDate > existing.startDate:
                latest_by_code[code] = row

        project_codes = sorted(latest_by_code.keys())
        projects = await self.repo.get_projects_by_codes(project_codes)
        by_code = {project.projectCode: project for project in projects}

        return [
            ProjectCodeNameResponse(
                project_code=code,
                project_name=by_code[code].projectName if code in by_code else code,
                role=(latest_by_code[code].role or None),
                allocated_hours=int(latest_by_code[code].allocatedHours),
                start_date=latest_by_code[code].startDate,
            )
            for code in project_codes
        ]
