from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.api.access import require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.tools.reporting_tool import ReportingTool

router = APIRouter()


@router.get("/reports/workforce/headcount-distribution", response_model=GenericResponse)
async def workforce_headcount_distribution(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).workforce_headcount_distribution(page=page, size=size, search=search)
    return GenericResponse(message="workforce headcount distribution fetched successfully", data=result.model_dump())


@router.get("/reports/workforce/role-wise-billed", response_model=GenericResponse)
async def workforce_role_wise_billed(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).workforce_role_wise_billed(page=page, size=size, search=search)
    return GenericResponse(message="workforce role-wise billed fetched successfully", data=result.model_dump())


@router.get("/reports/workforce/experience", response_model=GenericResponse)
async def workforce_experience(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).workforce_experience(page=page, size=size, search=search)
    return GenericResponse(message="workforce experience fetched successfully", data=result.model_dump())


@router.get("/reports/utilization/utilization-by-department", response_model=GenericResponse)
async def workforce_utilization_by_department(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).workforce_utilization_by_department(page=page, size=size, search=search, as_of=as_of)
    return GenericResponse(message="workforce utilization by department fetched successfully", data=result.model_dump())


@router.get("/reports/utilization/bench-aging", response_model=GenericResponse)
async def workforce_bench_aging(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).workforce_bench_aging(page=page, size=size, search=search, as_of=as_of)
    return GenericResponse(message="workforce bench aging fetched successfully", data=result.model_dump())


@router.get("/reports/skill-capacity/skill-inventory", response_model=GenericResponse)
async def skill_capacity_skill_inventory(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).skill_capacity_skill_inventory(page=page, size=size, search=search)
    return GenericResponse(message="skill capacity inventory fetched successfully", data=result.model_dump())


@router.get("/reports/compliance/contract-distribution", response_model=GenericResponse)
async def compliance_contract_distribution(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await ReportingTool(db).compliance_contract_distribution(page=page, size=size)
    return GenericResponse(message="compliance contract distribution fetched successfully", data=result.model_dump())

