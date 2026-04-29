from fastapi import APIRouter, Depends, Query, Request

from app.api.access import get_actor_email, require_any_role
from app.core.database import get_db
from app.schemas.allocation_extension import CreateAllocationExtensionRequest, UpdateAllocationExtensionStatusRequest
from app.schemas.common import GenericResponse
from app.tools.allocation_extension_tool import AllocationExtensionTool

router = APIRouter()


@router.post("/allocation-extension-request", response_model=GenericResponse)
async def create_allocation_extension_request(
    payload: CreateAllocationExtensionRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    request_id = await AllocationExtensionTool(db).create_request(get_actor_email(request), payload)
    return GenericResponse(message="success", data=request_id)


@router.get("/allocation-extension-request", response_model=GenericResponse)
async def list_allocation_extension_requests_for_hr(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await AllocationExtensionTool(db).list_for_hr(page=page, size=size, search=search, status_value=status)
    return GenericResponse(message="success", data=result.model_dump())


@router.put("/allocation-extension-request/status", response_model=GenericResponse)
async def update_allocation_extension_status(
    payload: UpdateAllocationExtensionStatusRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    request_id = await AllocationExtensionTool(db).update_status(get_actor_email(request), payload)
    return GenericResponse(message="success", data=request_id)


@router.get("/manager/allocation-extension-status", response_model=GenericResponse)
async def list_allocation_extension_requests_for_manager(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    search: str | None = Query(default=None),
    projectCode: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    result = await AllocationExtensionTool(db).list_for_manager(
        manager_email=get_actor_email(request),
        page=page,
        size=size,
        search=search,
        project_code=projectCode,
    )
    return GenericResponse(message="success", data=result.model_dump())
