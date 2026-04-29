from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request

from app.api.access import get_actor_email, get_actor_roles, require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.schemas.user_request import UserRequestCreate, UserRequestDelete, UserRequestStatusUpdate, UserRequestUpdate
from app.tools.user_request_tool import UserRequestTool

router = APIRouter()
_AUTHENTICATED = {"ROLE_EMPLOYEE", "ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"}


def _parse_java_or_iso_date(value: str):
    try:
        return datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError:
        return datetime.fromisoformat(value).date()


@router.post("/userRequest", response_model=GenericResponse)
async def create_user_request(payload: UserRequestCreate, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    request_id = await UserRequestTool(db).create_request(get_actor_email(request), payload)
    return GenericResponse(message="success", data=request_id)


@router.get("/userRequest/get/{fromDate}/{toDate}/{requestType}", response_model=GenericResponse)
@router.get("/userRequest/get/{empEmails}/{fromDate}/{toDate}/{requestType}", response_model=GenericResponse)
async def get_user_requests(
    fromDate: str,
    toDate: str,
    requestType: str,
    request: Request,
    empEmails: str | None = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=200),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    from_date = _parse_java_or_iso_date(fromDate)
    to_date = _parse_java_or_iso_date(toDate)
    emp_emails = [email.strip() for email in empEmails.split(",") if email.strip()] if empEmails else None
    response = await UserRequestTool(db).list_requests(
        actor_email=get_actor_email(request),
        actor_roles=get_actor_roles(request),
        from_date=from_date,
        to_date=to_date,
        request_type=requestType,
        page=page,
        size=size,
        emp_emails=emp_emails,
    )
    return GenericResponse(message="success", data=response.model_dump())


@router.put("/userRequest/status", response_model=GenericResponse)
async def update_user_request_status(
    payload: UserRequestStatusUpdate,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    request_id = await UserRequestTool(db).update_status(get_actor_email(request), get_actor_roles(request), payload)
    return GenericResponse(message="User request status updated successfully", data=request_id)


@router.put("/userRequest", response_model=GenericResponse)
async def update_user_request(payload: UserRequestUpdate, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    request_id = await UserRequestTool(db).update_request(get_actor_email(request), payload)
    return GenericResponse(message="User request updated successfully", data=request_id)


@router.delete("/userRequest", response_model=GenericResponse)
async def delete_user_request(payload: UserRequestDelete, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    result = await UserRequestTool(db).delete_request(get_actor_email(request), payload)
    return GenericResponse(message="User request deleted successfully", data=result)
