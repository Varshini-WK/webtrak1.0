from fastapi import APIRouter, Depends, Query, Request

from app.api.access import get_actor_email, require_any_role
from app.core.database import get_db
from app.schemas.bgv import BgvUpsertRequest
from app.schemas.common import GenericResponse
from app.tools.bgv_tool import BgvTool

router = APIRouter()


@router.post("/bgv/{emp_id}", response_model=GenericResponse)
async def upsert_bgv(emp_id: str, payload: BgvUpsertRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    actor_email = get_actor_email(request)
    result = await BgvTool(db).upsert_record(actor_email=actor_email, emp_id=emp_id, payload=payload)
    return GenericResponse(message="bgv record saved successfully", data=result.model_dump())


@router.get("/bgv/{emp_id}", response_model=GenericResponse)
async def get_bgv(emp_id: str, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await BgvTool(db).get_record(emp_id=emp_id)
    return GenericResponse(message="bgv record fetched successfully", data=result.model_dump())


@router.get("/bgv", response_model=GenericResponse)
async def list_bgv(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=10, ge=1, le=500),
    search: str | None = Query(default=None),
    overall_status: str | None = Query(default=None),
    employment_status: str | None = Query(default=None),
    reference_status: str | None = Query(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await BgvTool(db).list_dashboard(
        page=page,
        size=size,
        search=search,
        overall_status=overall_status,
        employment_status=employment_status,
        reference_status=reference_status,
    )
    return GenericResponse(message="bgv dashboard fetched successfully", data=result.model_dump())
