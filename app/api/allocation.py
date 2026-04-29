from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile

from app.api.access import get_actor_email, get_actor_roles, require_any_role
from app.core.database import get_db
from app.schemas.allocation import (
    AllocationCreateRequest,
    AllocationListResponse,
    AllocationRoleItem,
    AllocationRequestJava,
    AllocationResponse,
    AllocationUpdateRequest,
    ForecastAllocationResponse,
    UserAllocationItem,
)
from app.schemas.common import GenericResponse
from app.tools.allocation_tool import AllocationTool

router = APIRouter()

_HR_OR_ADMIN = frozenset({"ROLE_HR", "ROLE_ADMIN"})
_AUTHENTICATED = frozenset({"ROLE_HR", "ROLE_MANAGER", "ROLE_EMPLOYEE", "ROLE_ADMIN"})


@router.post("/allocation", response_model=GenericResponse)
async def create_allocation(
    payload: AllocationCreateRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _HR_OR_ADMIN)
    tool = AllocationTool(db)
    result = await tool.add_allocation(payload, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/allocation", response_model=GenericResponse)
async def list_allocations(
    request: Request,
    projectCode: str | None = Query(default=None),
    userEmail: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    view: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR"})
    tool = AllocationTool(db)
    result = await tool.list_allocations(
        project_code=projectCode,
        user_email=userEmail,
        search=search,
        page=page,
        size=size,
        view=view,
    )
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/allocation/roles", response_model=GenericResponse)
async def list_allocation_roles(
    request: Request,
    search: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _HR_OR_ADMIN)
    tool = AllocationTool(db)
    result = await tool.list_allocation_roles(search=search)
    return GenericResponse(message="success", data=[AllocationRoleItem.model_validate(x).model_dump() for x in result])


@router.get("/allocation/user", response_model=GenericResponse)
async def list_my_allocations(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    email = get_actor_email(request)
    tool = AllocationTool(db)
    result = await tool.list_my_allocations(email)
    return GenericResponse(message="success", data=[item.model_dump() for item in result])


@router.get("/allocation/forecasting", response_model=GenericResponse)
async def forecast_allocations(
    request: Request,
    days: int = Query(..., ge=1, le=3650),
    projectCode: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR"})
    tool = AllocationTool(db)
    result = await tool.forecast(
        days=days,
        project_code=projectCode,
        search=search,
        page=page,
        size=size,
    )
    return GenericResponse(message="success", data=result.model_dump())


@router.put("/allocation/{allocation_id}", response_model=GenericResponse)
async def update_allocation(
    allocation_id: int,
    payload: AllocationUpdateRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _HR_OR_ADMIN)
    tool = AllocationTool(db)
    result = await tool.update_allocation(allocation_id, payload, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result.model_dump())


@router.delete("/allocation/{allocation_id}", response_model=GenericResponse)
async def delete_allocation(
    allocation_id: int,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _HR_OR_ADMIN)
    tool = AllocationTool(db)
    result = await tool.delete_allocation(allocation_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result.model_dump())


@router.post("/allocation/batch", response_model=GenericResponse)
async def batch_import_allocations(
    request: Request,
    file: UploadFile = File(...),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_ADMIN"})
    content = await file.read()
    tool = AllocationTool(db)
    result = await tool.import_batch_excel(content, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.post("/allocation/update", response_model=GenericResponse)
async def update_allocation_java_contract(
    request: Request,
    allocationId: int = Query(...),
    payload: AllocationRequestJava | None = Body(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _HR_OR_ADMIN)
    tool = AllocationTool(db)
    actor_roles = get_actor_roles(request)
    if payload is None:
        deleted = await tool.delete_allocation(allocationId, actor_roles=actor_roles)
        return GenericResponse(message="success", data=deleted.model_dump())

    update_payload = AllocationUpdateRequest(
        employee_email=payload.employeeEmail,
        project_code=payload.projectCode,
        role=payload.role,
        allocated_hours=payload.allocatedHours,
        start_date=payload.startDate,
        end_date=payload.endDate,
        allocation_type=payload.allocationType,
        locked_in_date=payload.lockedInDate,
        is_manager=payload.isManager,
    )
    updated = await tool.update_allocation(allocationId, update_payload, actor_roles=actor_roles)
    return GenericResponse(message="success", data=updated.model_dump())
