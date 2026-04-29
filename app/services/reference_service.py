from datetime import UTC, datetime
import math

from fastapi import HTTPException, status

from app.repositories.designation_repository import DesignationRepository
from app.repositories.kpi_definition_repository import KpiDefinitionRepository
from app.repositories.reference_band_repository import ReferenceBandRepository
from app.repositories.submission_cycle_repository import SubmissionCycleRepository
from app.repositories.webknot_value_repository import WebknotValueRepository
from app.schemas import reference as schemas


def _now() -> datetime:
    return datetime.now(UTC)


def _pagination_meta(total: int, limit: int, offset: int) -> tuple[int, int, int]:
    page_size = max(1, min(limit, 100)) if limit else 20
    off = max(0, offset or 0)
    current_page = off // page_size if page_size else 0
    total_page = math.ceil(total / page_size) if total and page_size else 0
    return current_page, page_size, total_page


class ReferenceService:
    def __init__(self, db) -> None:
        self.db = db
        self.bands = ReferenceBandRepository(db)
        self.kpis = KpiDefinitionRepository(db)
        self.webknot = WebknotValueRepository(db)
        self.cycles = SubmissionCycleRepository(db)
        self.designations = DesignationRepository(db)

    async def list_bands(self, search: str | None) -> list[schemas.BandListItem]:
        rows = await self.bands.list_for_selection(search)
        return [
            schemas.BandListItem(
                id=row.id,
                name=row.name,
                stream=row.stream,
                designation=row.designation,
            )
            for row in rows
        ]

    # --- KPI ---

    async def list_kpi_definitions(
        self, limit: int | None, offset: int | None
    ) -> list[schemas.KpiDefinitionResponse] | schemas.PaginatedKpiDefinitions:
        if limit is not None or offset is not None:
            page_size = min(limit, 100) if limit is not None and limit > 0 else 20
            off = offset if offset is not None and offset >= 0 else 0
            rows, total = await self.kpis.list_paginated(page_size, off)
            current_page, ps, total_page = _pagination_meta(total, page_size, off)
            return schemas.PaginatedKpiDefinitions(
                data=[schemas.KpiDefinitionResponse.model_validate(r) for r in rows],
                current_page=current_page,
                page_size=ps,
                total_element=total,
                total_page=total_page,
            )
        rows = await self.kpis.list_all()
        return [schemas.KpiDefinitionResponse.model_validate(r) for r in rows]

    async def get_kpi_definition(self, kpi_id: int) -> schemas.KpiDefinitionResponse:
        row = await self.kpis.get_by_id(kpi_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI definition not found")
        return schemas.KpiDefinitionResponse.model_validate(row)

    async def create_kpi_definition(self, payload: schemas.KpiDefinitionCreate) -> schemas.KpiDefinitionResponse:
        if not await self._get_band(payload.band_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Band not found")

        if await self.kpis.exists_duplicate(
            payload.band_id,
            payload.department.value,
            payload.designation.strip(),
            payload.kpi_name.strip(),
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="KPI definition already exists for this band, department, designation, and name",
            )

        now = _now()
        data = {
            "band_id": payload.band_id,
            "department": payload.department.value,
            "designation": payload.designation.strip(),
            "kpi_name": payload.kpi_name.strip(),
            "weightage": payload.weightage,
            "active": payload.active,
            "created_at": now,
            "updated_at": now,
        }
        row = await self.kpis.create(data)
        return schemas.KpiDefinitionResponse.model_validate(row)

    async def _get_band(self, band_id: int):
        from sqlalchemy import select

        from app.models.band import Band

        async with self.db.session() as session:
            return await session.scalar(select(Band).where(Band.id == band_id))

    async def update_kpi_definition(self, kpi_id: int, payload: schemas.KpiDefinitionUpdate) -> schemas.KpiDefinitionResponse:
        existing = await self.kpis.get_by_id(kpi_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI definition not found")

        band_id = payload.band_id if payload.band_id is not None else existing.band_id
        department = payload.department.value if payload.department is not None else existing.department
        designation = payload.designation.strip() if payload.designation is not None else existing.designation
        kpi_name = payload.kpi_name.strip() if payload.kpi_name is not None else existing.kpi_name
        weightage = payload.weightage if payload.weightage is not None else existing.weightage
        active = payload.active if payload.active is not None else existing.active

        if not await self._get_band(band_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Band not found")

        if await self.kpis.exists_duplicate(band_id, department, designation, kpi_name, exclude_id=kpi_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another KPI definition already exists for this band, department, designation, and name",
            )

        now = _now()
        data = {
            "band_id": band_id,
            "department": department,
            "designation": designation,
            "kpi_name": kpi_name,
            "weightage": weightage,
            "active": active,
            "updated_at": now,
        }
        row = await self.kpis.update(kpi_id, data)
        assert row
        return schemas.KpiDefinitionResponse.model_validate(row)

    async def delete_kpi_definition(self, kpi_id: int) -> None:
        ok = await self.kpis.delete(kpi_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KPI definition not found")

    # --- Webknot ---

    async def list_webknot_values(
        self,
        limit: int | None,
        offset: int | None,
        active_only: bool | None,
    ) -> schemas.PaginatedWebknotValues:
        page_size = min(limit, 100) if limit is not None and limit > 0 else 20
        off = offset if offset is not None and offset >= 0 else 0
        rows, total = await self.webknot.list_paginated(page_size, off, active_only)
        current_page, ps, total_page = _pagination_meta(total, page_size, off)
        return schemas.PaginatedWebknotValues(
            data=[schemas.WebknotValueResponse.model_validate(r) for r in rows],
            current_page=current_page,
            page_size=ps,
            total_element=total,
            total_page=total_page,
        )

    async def create_webknot_value(self, payload: schemas.WebknotValueCreate) -> schemas.WebknotValueResponse:
        now = _now()
        data = {
            "title": payload.title.strip(),
            "evaluation_criteria": payload.evaluation_criteria,
            "active": payload.active,
            "created_at": now,
            "updated_at": now,
        }
        row = await self.webknot.create(data)
        return schemas.WebknotValueResponse.model_validate(row)

    async def update_webknot_value(self, row_id: int, payload: schemas.WebknotValueUpdate) -> schemas.WebknotValueResponse:
        existing = await self.webknot.get_by_id(row_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webknot value not found")

        data: dict = {"updated_at": _now()}
        if payload.title is not None:
            data["title"] = payload.title.strip()
        if payload.evaluation_criteria is not None:
            data["evaluation_criteria"] = payload.evaluation_criteria
        if payload.active is not None:
            data["active"] = payload.active

        row = await self.webknot.update(row_id, data)
        assert row
        return schemas.WebknotValueResponse.model_validate(row)

    async def delete_webknot_value(self, row_id: int) -> None:
        ok = await self.webknot.delete(row_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webknot value not found")

    # --- Submission cycles ---

    async def list_submission_cycles(
        self, limit: int | None, offset: int | None
    ) -> list[schemas.SubmissionCycleResponse] | schemas.PaginatedSubmissionCycles:
        if limit is not None or offset is not None:
            page_size = min(limit, 100) if limit is not None and limit > 0 else 20
            off = offset if offset is not None and offset >= 0 else 0
            rows, total = await self.cycles.list_paginated(page_size, off)
            current_page, ps, total_page = _pagination_meta(total, page_size, off)
            return schemas.PaginatedSubmissionCycles(
                data=[schemas.SubmissionCycleResponse.model_validate(r) for r in rows],
                current_page=current_page,
                page_size=ps,
                total_element=total,
                total_page=total_page,
            )
        rows = await self.cycles.list_all()
        return [schemas.SubmissionCycleResponse.model_validate(r) for r in rows]

    async def get_submission_cycle(self, cycle_id: int) -> schemas.SubmissionCycleResponse:
        row = await self.cycles.get_by_id(cycle_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission cycle not found")
        return schemas.SubmissionCycleResponse.model_validate(row)

    async def get_submission_cycle_by_key_scope(
        self, cycle_key: str, scope: str | None
    ) -> schemas.SubmissionCycleResponse:
        from app.models.submission_cycle import SubmissionCycle

        sc = scope or SubmissionCycle.SCOPE_GLOBAL
        row = await self.cycles.get_by_cycle_key_and_scope(cycle_key.strip(), sc)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission cycle not found")
        return schemas.SubmissionCycleResponse.model_validate(row)

    async def create_submission_cycle(self, payload: schemas.SubmissionCycleCreate) -> schemas.SubmissionCycleResponse:
        from app.models.submission_cycle import SubmissionCycle

        scope = (payload.scope or "").strip() or SubmissionCycle.SCOPE_GLOBAL
        ck = payload.cycle_key.strip()
        if len(ck) > 7:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cycle key must be at most 7 characters")

        if await self.cycles.exists_duplicate(ck, scope):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Submission cycle already exists for this cycle key and scope",
            )

        now = _now()
        data = {
            "cycle_key": ck,
            "scope": scope,
            "window_start_at": payload.window_start_at,
            "window_end_at": payload.window_end_at,
            "manual_closed": payload.manual_closed,
            "updated_by": payload.updated_by,
            "created_at": now,
            "updated_at": now,
        }
        row = await self.cycles.create(data)
        return schemas.SubmissionCycleResponse.model_validate(row)

    async def update_submission_cycle(self, cycle_id: int, payload: schemas.SubmissionCycleUpdate) -> schemas.SubmissionCycleResponse:
        from app.models.submission_cycle import SubmissionCycle

        existing = await self.cycles.get_by_id(cycle_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission cycle not found")

        ck = payload.cycle_key.strip() if payload.cycle_key is not None else existing.cycle_key
        if len(ck) > 7:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cycle key must be at most 7 characters")

        scope = (
            (payload.scope or "").strip() or SubmissionCycle.SCOPE_GLOBAL
            if payload.scope is not None
            else existing.scope
        )

        if await self.cycles.exists_duplicate(ck, scope, exclude_id=cycle_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another submission cycle already exists for this cycle key and scope",
            )

        now = _now()
        data = {
            "cycle_key": ck,
            "scope": scope,
            "window_start_at": payload.window_start_at if payload.window_start_at is not None else existing.window_start_at,
            "window_end_at": payload.window_end_at if payload.window_end_at is not None else existing.window_end_at,
            "manual_closed": payload.manual_closed if payload.manual_closed is not None else existing.manual_closed,
            "updated_by": payload.updated_by if payload.updated_by is not None else existing.updated_by,
            "updated_at": now,
        }
        row = await self.cycles.update(cycle_id, data)
        assert row
        return schemas.SubmissionCycleResponse.model_validate(row)

    async def delete_submission_cycle(self, cycle_id: int) -> None:
        ok = await self.cycles.delete(cycle_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission cycle not found")

    # --- Designations ---

    async def list_designations(self, band_id: int, department: str) -> list[schemas.DesignationResponse]:
        rows = await self.designations.list_by_band_and_department(band_id, department.strip())
        return [schemas.DesignationResponse.model_validate(r) for r in rows]
