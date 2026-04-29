from fastapi import HTTPException, status

from app.repositories.project_repository import ProjectRepository
from app.schemas.project import (
    CreateProjectRequest,
    ManagerProjectsResponse,
    ProjectCodeNameResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSimpleListResponse,
    ProjectWithEmployeesResponse,
)


SYSTEM_PROJECT_CODES = {"BENCH", "GLOBAL"}


class ProjectService:
    def __init__(self, db) -> None:
        self.repo = ProjectRepository(db)

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
        return ProjectResponse(
            project_code=project.projectCode,
            project_name=project.projectName,
            project_type=project.projectType,
            is_active=project.isActive,
        )

    async def create_project(self, payload: CreateProjectRequest) -> ProjectResponse:
        project_code = self._clean_project_code(payload.project_code)
        project_name = self._clean_project_name(payload.project_name)

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

    async def get_project_codes_for_user(self, email: str) -> list[ProjectCodeNameResponse]:
        user = await self.repo.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        allocations = await self.repo.get_active_allocations_for_user(user.id)
        project_codes = sorted({row.projectCode for row in allocations if row.projectCode and row.projectCode not in SYSTEM_PROJECT_CODES})
        projects = await self.repo.get_projects_by_codes(project_codes)
        by_code = {project.projectCode: project for project in projects}

        return [
            ProjectCodeNameResponse(project_code=code, project_name=by_code[code].projectName if code in by_code else code)
            for code in project_codes
        ]
