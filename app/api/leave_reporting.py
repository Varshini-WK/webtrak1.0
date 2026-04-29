from fastapi import APIRouter, Depends, Query, Request

from app.api.access import require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.tools.leave_reporting_tool import LeaveReportingTool

router = APIRouter()


@router.get("/leave-summary", response_model=GenericResponse)
async def fetch_leave_summary(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    search: str | None = Query(default=None),
    type: str | None = Query(default=None),
    band: str | None = Query(default=None),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await LeaveReportingTool(db).fetch_leave_summary(
        page=page,
        size=size,
        search=search,
        user_type=type,
        band=band,
        year=year,
        month=month,
    )
    return GenericResponse(message="leave summary fetched successfully", data=result.model_dump())

