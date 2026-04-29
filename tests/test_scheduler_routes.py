import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api.scheduler import run_all_scheduler_jobs


def _request(headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {"type": "http", "method": "POST", "path": "/api/v1/scheduler/run-all", "headers": hdrs}
    return Request(scope)


def test_scheduler_run_all_blocked_in_prod() -> None:
    with patch("app.api.scheduler.get_settings") as mock_settings:
        mock_settings.return_value = type("S", (), {"app_env": "prod"})()
        request = _request(headers={"cookie": "roles=ROLE_ADMIN"})
        try:
            asyncio.run(run_all_scheduler_jobs(request, db=MagicMock()))
            raise AssertionError("Expected HTTPException")
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "blocked in production" in str(exc.detail)


def test_scheduler_run_all_requires_role() -> None:
    with patch("app.api.scheduler.get_settings") as mock_settings:
        mock_settings.return_value = type("S", (), {"app_env": "dev"})()
        request = _request(headers={"cookie": "roles=ROLE_EMPLOYEE"})
        try:
            asyncio.run(run_all_scheduler_jobs(request, db=MagicMock()))
            raise AssertionError("Expected HTTPException")
        except HTTPException as exc:
            assert exc.status_code == 403
            assert exc.detail == "Insufficient role"


def test_scheduler_run_all_returns_summary() -> None:
    fake_summary = {
        "total_jobs": 7,
        "success_jobs": 7,
        "failed_jobs": 0,
        "results": [],
    }
    with patch("app.api.scheduler.get_settings") as mock_settings:
        mock_settings.return_value = type("S", (), {"app_env": "dev"})()
        with patch("app.api.scheduler.ScheduledJobsService.run_all_jobs", new=AsyncMock(return_value=fake_summary)):
            request = _request(headers={"cookie": "roles=ROLE_HR"})
            response = asyncio.run(run_all_scheduler_jobs(request, db=MagicMock()))
            assert response.message == "Scheduler jobs executed"
            assert response.data["total_jobs"] == 7
            assert response.data["failed_jobs"] == 0

