from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.access import get_actor_email, get_actor_roles, require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.schemas.timelog import (
    TimeLogCreateRequest,
    TimeLogListResponse,
    TimeLogResponse,
    TimeLogStatusBatchRequest,
    TimeLogStatusUpdateRequest,
    TimeLogUpdateRequest,
    UpdateTimeLogEntryRequestJava,
)
from app.tools.timelog_tool import TimeLogTool

router = APIRouter()

_AUTHENTICATED = frozenset({"ROLE_HR", "ROLE_MANAGER", "ROLE_EMPLOYEE", "ROLE_ADMIN"})


def _parse_flexible_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError:
        return date.fromisoformat(value)


@router.post("/timelog", response_model=GenericResponse)
async def submit_timelog(payload: TimeLogCreateRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    result = await TimeLogTool(db).submit(get_actor_email(request), payload)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/timelog", response_model=GenericResponse)
async def list_my_timelogs(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    result = await TimeLogTool(db).list_my_logs(get_actor_email(request), page, size)
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/timelog/get/{empEmail}/{logDate}", response_model=GenericResponse)
async def get_timelogs_java_contract(
    empEmail: str,
    logDate: str,
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    parsed_date: date
    try:
        parsed_date = datetime.strptime(logDate, "%d-%m-%Y").date()
    except ValueError:
        parsed_date = date.fromisoformat(logDate)
    actor_email = get_actor_email(request).strip().lower()
    actor_roles = get_actor_roles(request)
    target = empEmail.strip().lower()
    allowed = actor_email == target or bool(actor_roles.intersection({"ROLE_HR", "ROLE_ADMIN", "ROLE_MANAGER"}))
    if not allowed:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized user")
    result = await TimeLogTool(db).list_logs_by_user_and_date(
        actor_email=actor_email,
        actor_roles=actor_roles,
        employee_email=target,
        log_date=parsed_date,
        page=page,
        size=size,
    )
    return GenericResponse(message="success", data=result.model_dump())


@router.put("/timelog/{timelog_id:int}", response_model=GenericResponse)
async def edit_timelog(
    timelog_id: int,
    payload: TimeLogUpdateRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    result = await TimeLogTool(db).edit(get_actor_email(request), timelog_id, payload)
    return GenericResponse(message="success", data=result.model_dump())


@router.delete("/timelog/{timelog_id:int}", response_model=GenericResponse)
async def delete_timelog(timelog_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    result = await TimeLogTool(db).delete(get_actor_email(request), timelog_id)
    return GenericResponse(message=result.get("message", "success"), data=None)


@router.put("/timelog/entry", response_model=GenericResponse)
async def update_timelog_entry_java_contract(
    payload: UpdateTimeLogEntryRequestJava,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    result = await TimeLogTool(db).update_entry_java(
        actor_email=get_actor_email(request),
        timelog_id=payload.timeLogId,
        description=payload.description,
        logged_hours=payload.loggedHours,
    )
    return GenericResponse(message="success", data=result.model_dump())


@router.put("/timelog/status", response_model=GenericResponse)
async def update_timelog_status(payload: TimeLogStatusUpdateRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    result = await TimeLogTool(db).update_status_single(
        actor_email=get_actor_email(request),
        actor_roles=get_actor_roles(request),
        payload=payload,
    )
    return GenericResponse(message="success", data=result.model_dump())


@router.put("/timelog/status/batch", response_model=GenericResponse)
async def update_timelog_status_batch(payload: TimeLogStatusBatchRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    result = await TimeLogTool(db).update_status_batch(
        actor_email=get_actor_email(request),
        actor_roles=get_actor_roles(request),
        payload=payload,
    )
    return GenericResponse(message="success", data=result)


@router.get("/export/timelogs")
async def export_timelogs(
    request: Request,
    startDate: date = Query(...),
    endDate: date = Query(...),
    projectCode: str | None = Query(default=None),
    empEmail: str | None = Query(default=None),
    format: str = Query(default="csv"),
    db=Depends(get_db),
) -> StreamingResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    tool = TimeLogTool(db)
    fmt = format.strip().lower()
    if fmt not in {"csv", "xlsx"}:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be csv or xlsx")
    if fmt == "csv":
        csv_data = await tool.export_csv(
            actor_email=get_actor_email(request),
            actor_roles=get_actor_roles(request),
            project_code=projectCode,
            employee_email=empEmail,
            start_date=startDate,
            end_date=endDate,
        )
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=timelogs.csv"},
        )

    rows = await tool.export_rows(
        actor_email=get_actor_email(request),
        actor_roles=get_actor_roles(request),
        project_code=projectCode,
        employee_email=empEmail,
        start_date=startDate,
        end_date=endDate,
    )
    xlsx_data = await tool.build_project_summary_xlsx(rows)
    return StreamingResponse(
        iter([xlsx_data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=project_time_logs.xlsx"},
    )


@router.get("/export/timelogs/{projectCode}/{empEmail}/{startDate}/{endDate}")
async def export_employee_timelogs_xlsx_legacy(
    projectCode: str,
    empEmail: str,
    startDate: str,
    endDate: str,
    request: Request,
    db=Depends(get_db),
) -> StreamingResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    tool = TimeLogTool(db)
    rows = await tool.export_rows(
        actor_email=get_actor_email(request),
        actor_roles=get_actor_roles(request),
        project_code=projectCode,
        employee_email=empEmail,
        start_date=_parse_flexible_date(startDate),
        end_date=_parse_flexible_date(endDate),
    )
    xlsx_data = tool.build_time_logs_xlsx(rows)
    return StreamingResponse(
        iter([xlsx_data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=time_logs.xlsx"},
    )


@router.get("/export/timelogs/{startDate}/{endDate}")
@router.get("/export/timelogs/{projectCode}/{startDate}/{endDate}")
async def export_project_timelogs_xlsx_legacy(
    startDate: str,
    endDate: str,
    request: Request,
    projectCode: str | None = None,
    empEmail: str | None = Query(default=None),
    db=Depends(get_db),
) -> StreamingResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    tool = TimeLogTool(db)
    rows = await tool.export_rows(
        actor_email=get_actor_email(request),
        actor_roles=get_actor_roles(request),
        project_code=projectCode,
        employee_email=empEmail,
        start_date=_parse_flexible_date(startDate),
        end_date=_parse_flexible_date(endDate),
    )
    xlsx_data = await tool.build_project_summary_xlsx(rows)
    return StreamingResponse(
        iter([xlsx_data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=project_time_logs.xlsx"},
    )
