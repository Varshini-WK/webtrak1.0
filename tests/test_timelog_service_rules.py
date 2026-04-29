from datetime import date
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.schemas.timelog import TimeLogStatusUpdateRequest
from app.services.timelog_service import TimeLogService


def _mk_row(project_code: str = "PROJ1"):
    row = MagicMock()
    row.projectCode = project_code
    row.employeeEmail = "employee@webknot.in"
    row.status = "SUBMITTED"
    return row


async def _run(coro):
    return await coro


def test_manager_scope_denied_when_not_project_manager() -> None:
    svc = TimeLogService(MagicMock())
    svc._actor_user = AsyncMock(return_value=MagicMock(id=12))
    svc.repo.is_manager_for_project = AsyncMock(return_value=False)
    try:
        import asyncio

        asyncio.run(svc._assert_manager_scope("manager@webknot.in", {"ROLE_MANAGER"}, "PROJ1"))
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail["code"] == "MANAGER_SCOPE_DENIED"


def test_single_status_404_when_missing_timelog() -> None:
    svc = TimeLogService(MagicMock())
    svc.repo.get_by_id = AsyncMock(return_value=None)
    payload = TimeLogStatusUpdateRequest(timelog_id=11, status="APPROVED")
    try:
        import asyncio

        asyncio.run(
            svc.update_status_single(
                actor_email="manager@webknot.in",
                actor_roles={"ROLE_MANAGER"},
                payload=payload,
            )
        )
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail["code"] == "TIMELOG_NOT_FOUND"
