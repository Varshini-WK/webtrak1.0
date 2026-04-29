from app.schemas.project import (
    CreateProjectRequest,
    ManagerProjectsResponse,
    ProjectCodeNameResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSimpleListResponse,
)
from app.services.project_service import ProjectService


class ProjectTool:
    def __init__(self, db) -> None:
        self.service = ProjectService(db)

    async def create_project(self, payload: CreateProjectRequest) -> ProjectResponse:
        return await self.service.create_project(payload)

    async def bulk_create(self, payload: list[CreateProjectRequest]) -> list[ProjectResponse]:
        return await self.service.bulk_create(payload)

    async def get_project_by_code(self, project_code: str) -> ProjectResponse:
        return await self.service.get_project_by_code(project_code)

    async def get_all_projects(self, page: int, size: int, search: str | None) -> ProjectListResponse:
        return await self.service.get_all_projects(page, size, search)

    async def get_all_projects_without_pagination(self, search: str | None) -> ProjectSimpleListResponse:
        return await self.service.get_all_projects_without_pagination(search)

    async def get_manager_projects(self, manager_email: str) -> ManagerProjectsResponse:
        return await self.service.get_manager_projects(manager_email, include_roles=False)

    async def get_manager_projects_with_roles(self, manager_email: str) -> ManagerProjectsResponse:
        return await self.service.get_manager_projects(manager_email, include_roles=True)

    async def get_project_assigned_to_user(self, email: str) -> list[ProjectCodeNameResponse]:
        return await self.service.get_project_codes_for_user(email)
