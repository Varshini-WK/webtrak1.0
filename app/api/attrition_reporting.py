from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.access import require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.tools.reporting_tool import ReportingTool

router = APIRouter()

FyStartYearQuery = Annotated[
    int,
    Query(..., ge=2000, le=2100, description="Calendar year in which FY starts (1 April)"),
]


def _attrition_tool(db):
    return ReportingTool(db)


@router.get("/reports/attrition/overall-percent", response_model=GenericResponse)
async def attrition_overall_percent(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_overall_percent(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition overall percent (5.1) fetched successfully", data=result.model_dump())


@router.get("/reports/attrition/voluntary-involuntary", response_model=GenericResponse)
async def attrition_voluntary_involuntary(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_voluntary_involuntary(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition voluntary vs involuntary (5.2) fetched successfully", data=result.model_dump())


@router.get("/reports/attrition/role-wise", response_model=GenericResponse)
async def attrition_role_wise(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_role_wise(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition role-wise fetched successfully", data=result.model_dump())


@router.get("/reports/attrition/manager-wise", response_model=GenericResponse)
async def attrition_manager_wise(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_manager_wise(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition manager-wise fetched successfully", data=result.model_dump())


@router.get("/reports/attrition/critical-skill", response_model=GenericResponse)
async def attrition_critical_skill(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_critical_skill(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition critical skill (5.4) fetched successfully", data=result.model_dump())


@router.get("/reports/attrition/regretted", response_model=GenericResponse)
async def attrition_regretted(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_regretted(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition regretted (5.5) fetched successfully", data=result.model_dump())


@router.get("/reports/attrition/average-tenure", response_model=GenericResponse)
async def attrition_average_tenure(
    request: Request,
    fy_start_year: FyStartYearQuery,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await _attrition_tool(db).attrition_average_tenure(fy_start_year=fy_start_year)
    return GenericResponse(message="attrition average tenure (5.6) fetched successfully", data=result.model_dump())


