import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api.timelog import export_employee_timelogs_xlsx_legacy, export_project_timelogs_xlsx_legacy, export_timelogs


def _request(path: str, headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {"type": "http", "method": "GET", "path": path, "headers": hdrs}
    return Request(scope)


def test_export_timelogs_rejects_invalid_format() -> None:
    request = _request("/api/v1/export/timelogs", headers={"cookie": "roles=ROLE_HR; email=hr@x.com"})
    try:
        asyncio.run(
            export_timelogs(
                request=request,
                startDate=date(2026, 1, 1),
                endDate=date(2026, 1, 2),
                format="pdf",
                db=MagicMock(),
            )
        )
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400


def test_legacy_employee_export_returns_stream() -> None:
    request = _request("/api/v1/export/timelogs/P1/u@x.com/01-01-2026/02-01-2026", headers={"cookie": "roles=ROLE_HR; email=hr@x.com"})
    with patch("app.api.timelog.TimeLogTool.export_rows", new=AsyncMock(return_value=[])):
        with patch("app.api.timelog.TimeLogTool.build_time_logs_xlsx", return_value=b"xlsx"):
            response = asyncio.run(
                export_employee_timelogs_xlsx_legacy(
                    projectCode="P1",
                    empEmail="u@x.com",
                    startDate="01-01-2026",
                    endDate="02-01-2026",
                    request=request,
                    db=MagicMock(),
                )
            )
            assert "attachment; filename=time_logs.xlsx" in response.headers["content-disposition"]


def test_legacy_project_export_returns_stream() -> None:
    request = _request("/api/v1/export/timelogs/01-01-2026/02-01-2026", headers={"cookie": "roles=ROLE_HR; email=hr@x.com"})
    with patch("app.api.timelog.TimeLogTool.export_rows", new=AsyncMock(return_value=[])):
        with patch("app.api.timelog.TimeLogTool.build_project_summary_xlsx", new=AsyncMock(return_value=b"xlsx")):
            response = asyncio.run(
                export_project_timelogs_xlsx_legacy(
                    startDate="01-01-2026",
                    endDate="02-01-2026",
                    request=request,
                    db=MagicMock(),
                )
            )
            assert "attachment; filename=project_time_logs.xlsx" in response.headers["content-disposition"]

