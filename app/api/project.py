from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.api.access import get_actor_email, require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.schemas.project import (
    CreateProjectRequest,
    ManagerProjectsResponse,
    ProjectCodeNameResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectSimpleListResponse,
)
from app.tools.project_tool import ProjectTool

router = APIRouter()


@router.post("/project", response_model=GenericResponse)
async def create_project(payload: CreateProjectRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ProjectTool(db).create_project(payload)
    return GenericResponse(message="success", data=result.model_dump())


@router.post("/projects", response_model=GenericResponse)
async def create_projects(payload: list[CreateProjectRequest], request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_ADMIN"})
    result = await ProjectTool(db).bulk_create(payload)
    return GenericResponse(message="success", data=[item.model_dump() for item in result])


@router.get("/projects", response_model=GenericResponse)
async def get_all_projects(
    request: Request,
    page: int = 0,
    size: int = 10,
    search: str | None = None,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ProjectTool(db).get_all_projects(page=page, size=size, search=search)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/projects/all", response_model=GenericResponse)
async def get_all_projects_without_pagination(
    request: Request,
    search: str | None = None,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ProjectTool(db).get_all_projects_without_pagination(search=search)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/project", response_model=GenericResponse)
async def get_project(
    request: Request,
    projectCode: str = Query(...),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ProjectTool(db).get_project_by_code(projectCode)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/manager-projects", response_model=GenericResponse)
async def get_manager_projects(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER"})
    email = get_actor_email(request)
    result = await ProjectTool(db).get_manager_projects(email)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/manager-projects-with-roles", response_model=GenericResponse)
async def get_manager_projects_with_roles(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER"})
    email = get_actor_email(request)
    result = await ProjectTool(db).get_manager_projects_with_roles(email)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/manager-team-on-leave-today", response_model=GenericResponse)
async def get_manager_team_on_leave_today(
    request: Request,
    as_of_date: date | None = Query(default=None, alias="asOfDate"),
    db=Depends(get_db),
) -> GenericResponse:
    """Team members on DEDUCT leave for the given day on projects where the caller is project manager."""
    require_any_role(request, {"ROLE_MANAGER"})
    email = get_actor_email(request)
    result = await ProjectTool(db).get_manager_team_on_leave_today(email, as_of_date)
    return GenericResponse(message="success", data=result.model_dump(mode="json"))


@router.get("/project-assigned-to-user", response_model=GenericResponse)
async def get_project_assigned_to_user(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_MANAGER", "ROLE_EMPLOYEE", "ROLE_ADMIN"})
    email = get_actor_email(request)
    result = await ProjectTool(db).get_project_assigned_to_user(email)
    return GenericResponse(message="success", data=[item.model_dump() for item in result])
