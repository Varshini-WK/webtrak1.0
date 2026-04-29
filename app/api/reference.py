"""Reference data APIs (canonical paths under `/api/v1/masters/`).

Legacy Spring paths (for migration reference; not implemented as aliases here):
- `GET /api/v1/band-list` → `GET /api/v1/masters/bands`
- KPI: `/list-kpi-definitions`, `/get-kpi-definition/{id}`, `/add-kpi-definition`, etc. → `/api/v1/masters/kpi-definitions`
- Webknot: `/webknot-value/list`, `/webknot-value/add`, ... → `/api/v1/masters/webknot-values`
- Submission cycles: `/list-submission-cycles`, ... → `/api/v1/masters/submission-cycles`
- Designations: `GET /designations?bandId=&department=` → `GET /api/v1/masters/designations?band_id=&department=`
"""

from typing import Union

from fastapi import APIRouter, Depends, Query, Request

from app.api.access import require_any_role
from app.core.database import get_db
from app.schemas.reference import (
    BandListItem,
    DesignationResponse,
    KpiDefinitionCreate,
    KpiDefinitionResponse,
    KpiDefinitionUpdate,
    PaginatedKpiDefinitions,
    PaginatedSubmissionCycles,
    PaginatedWebknotValues,
    SubmissionCycleCreate,
    SubmissionCycleResponse,
    SubmissionCycleUpdate,
    WebknotValueCreate,
    WebknotValueResponse,
    WebknotValueUpdate,
)
from app.services.reference_service import ReferenceService

router = APIRouter()

_READ_ROLES = frozenset({"ROLE_HR", "ROLE_MANAGER", "ROLE_EMPLOYEE", "ROLE_ADMIN"})
_WRITE_ROLES = frozenset({"ROLE_HR", "ROLE_ADMIN"})


def _svc(db=Depends(get_db)) -> ReferenceService:
    return ReferenceService(db)


# --- Bands ---


@router.get("/masters/bands", response_model=list[BandListItem])
async def list_bands(
    request: Request,
    search: str | None = None,
    svc: ReferenceService = Depends(_svc),
) -> list[BandListItem]:
    require_any_role(request, _READ_ROLES)
    return await svc.list_bands(search)


# --- KPI definitions ---


@router.get("/masters/kpi-definitions", response_model=Union[list[KpiDefinitionResponse], PaginatedKpiDefinitions])
async def list_kpi_definitions(
    request: Request,
    limit: int | None = None,
    offset: int | None = None,
    svc: ReferenceService = Depends(_svc),
):
    require_any_role(request, _READ_ROLES)
    return await svc.list_kpi_definitions(limit, offset)


@router.get("/masters/kpi-definitions/{kpi_id}", response_model=KpiDefinitionResponse)
async def get_kpi_definition(
    request: Request,
    kpi_id: int,
    svc: ReferenceService = Depends(_svc),
) -> KpiDefinitionResponse:
    require_any_role(request, _READ_ROLES)
    return await svc.get_kpi_definition(kpi_id)


@router.post("/masters/kpi-definitions", response_model=KpiDefinitionResponse)
async def create_kpi_definition(
    request: Request,
    payload: KpiDefinitionCreate,
    svc: ReferenceService = Depends(_svc),
) -> KpiDefinitionResponse:
    require_any_role(request, _WRITE_ROLES)
    return await svc.create_kpi_definition(payload)


@router.put("/masters/kpi-definitions/{kpi_id}", response_model=KpiDefinitionResponse)
async def update_kpi_definition(
    request: Request,
    kpi_id: int,
    payload: KpiDefinitionUpdate,
    svc: ReferenceService = Depends(_svc),
) -> KpiDefinitionResponse:
    require_any_role(request, _WRITE_ROLES)
    return await svc.update_kpi_definition(kpi_id, payload)


@router.delete("/masters/kpi-definitions/{kpi_id}")
async def delete_kpi_definition(
    request: Request,
    kpi_id: int,
    svc: ReferenceService = Depends(_svc),
) -> dict[str, str]:
    require_any_role(request, _WRITE_ROLES)
    await svc.delete_kpi_definition(kpi_id)
    return {"message": "deleted"}


# --- Webknot values ---


@router.get("/masters/webknot-values", response_model=PaginatedWebknotValues)
async def list_webknot_values(
    request: Request,
    limit: int | None = None,
    offset: int | None = None,
    active_only: bool | None = Query(default=None),
    svc: ReferenceService = Depends(_svc),
) -> PaginatedWebknotValues:
    require_any_role(request, _READ_ROLES)
    return await svc.list_webknot_values(limit, offset, active_only)


@router.post("/masters/webknot-values", response_model=WebknotValueResponse)
async def create_webknot_value(
    request: Request,
    payload: WebknotValueCreate,
    svc: ReferenceService = Depends(_svc),
) -> WebknotValueResponse:
    require_any_role(request, _WRITE_ROLES)
    return await svc.create_webknot_value(payload)


@router.put("/masters/webknot-values/{row_id}", response_model=WebknotValueResponse)
async def update_webknot_value(
    request: Request,
    row_id: int,
    payload: WebknotValueUpdate,
    svc: ReferenceService = Depends(_svc),
) -> WebknotValueResponse:
    require_any_role(request, _WRITE_ROLES)
    return await svc.update_webknot_value(row_id, payload)


@router.delete("/masters/webknot-values/{row_id}")
async def delete_webknot_value(
    request: Request,
    row_id: int,
    svc: ReferenceService = Depends(_svc),
) -> dict[str, str]:
    require_any_role(request, _WRITE_ROLES)
    await svc.delete_webknot_value(row_id)
    return {"message": "deleted"}


# --- Submission cycles ---


@router.get("/masters/submission-cycles", response_model=Union[list[SubmissionCycleResponse], PaginatedSubmissionCycles])
async def list_submission_cycles(
    request: Request,
    limit: int | None = None,
    offset: int | None = None,
    svc: ReferenceService = Depends(_svc),
):
    require_any_role(request, _READ_ROLES)
    return await svc.list_submission_cycles(limit, offset)


@router.get("/masters/submission-cycles/by-key", response_model=SubmissionCycleResponse)
async def get_submission_cycle_by_key(
    request: Request,
    cycle_key: str = Query(...),
    scope: str | None = Query(default=None),
    svc: ReferenceService = Depends(_svc),
) -> SubmissionCycleResponse:
    require_any_role(request, _READ_ROLES)
    return await svc.get_submission_cycle_by_key_scope(cycle_key, scope)


@router.get("/masters/submission-cycles/{cycle_id}", response_model=SubmissionCycleResponse)
async def get_submission_cycle(
    request: Request,
    cycle_id: int,
    svc: ReferenceService = Depends(_svc),
) -> SubmissionCycleResponse:
    require_any_role(request, _READ_ROLES)
    return await svc.get_submission_cycle(cycle_id)


@router.post("/masters/submission-cycles", response_model=SubmissionCycleResponse)
async def create_submission_cycle(
    request: Request,
    payload: SubmissionCycleCreate,
    svc: ReferenceService = Depends(_svc),
) -> SubmissionCycleResponse:
    require_any_role(request, _WRITE_ROLES)
    return await svc.create_submission_cycle(payload)


@router.put("/masters/submission-cycles/{cycle_id}", response_model=SubmissionCycleResponse)
async def update_submission_cycle(
    request: Request,
    cycle_id: int,
    payload: SubmissionCycleUpdate,
    svc: ReferenceService = Depends(_svc),
) -> SubmissionCycleResponse:
    require_any_role(request, _WRITE_ROLES)
    return await svc.update_submission_cycle(cycle_id, payload)


@router.delete("/masters/submission-cycles/{cycle_id}")
async def delete_submission_cycle(
    request: Request,
    cycle_id: int,
    svc: ReferenceService = Depends(_svc),
) -> dict[str, str]:
    require_any_role(request, _WRITE_ROLES)
    await svc.delete_submission_cycle(cycle_id)
    return {"message": "deleted"}


# --- Designations ---


@router.get("/masters/designations", response_model=list[DesignationResponse])
async def list_designations(
    request: Request,
    band_id: int = Query(..., gt=0),
    department: str = Query(..., min_length=1),
    svc: ReferenceService = Depends(_svc),
) -> list[DesignationResponse]:
    require_any_role(request, _READ_ROLES)
    return await svc.list_designations(band_id, department)
