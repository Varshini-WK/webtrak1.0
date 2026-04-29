import asyncio
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.datastructures import UploadFile
from starlette.requests import Request

from app.api.employee import upload_leave_excel
from app.api.leave_reporting import fetch_leave_summary
from app.schemas.leave_reporting import LeaveSummaryPage


def _request(path: str, headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {"type": "http", "method": "POST", "path": path, "headers": hdrs}
    return Request(scope)


def test_leave_summary_requires_hr_or_admin() -> None:
    request = _request("/api/v1/leave-summary", headers={"cookie": "roles=ROLE_EMPLOYEE"})
    try:
        asyncio.run(fetch_leave_summary(request=request, db=MagicMock()))
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Insufficient role"


def test_leave_summary_success_payload() -> None:
    request = _request("/api/v1/leave-summary", headers={"cookie": "roles=ROLE_HR"})
    fake = LeaveSummaryPage(current_page=0, total_page=1, page_size=10, total_element=1, data=[])
    with patch("app.api.leave_reporting.LeaveReportingTool.fetch_leave_summary", new=AsyncMock(return_value=fake)):
        response = asyncio.run(fetch_leave_summary(request=request, db=MagicMock()))
        assert response.message == "leave summary fetched successfully"
        assert response.data["total_element"] == 1


def test_upload_leave_excel_success() -> None:
    request = _request("/api/v1/upload", headers={"cookie": "roles=ROLE_ADMIN; email=admin@x.com"})
    upload = UploadFile(filename="leave.xlsx", file=BytesIO(b"fake"))
    with patch("app.api.employee.EmployeeTool.import_leave_data", new=AsyncMock(return_value={"processed": 1, "skipped": 0})):
        with patch("app.api.employee.UserRepository.get_by_email", new=AsyncMock(return_value=type("U", (), {"id": 1})())):
            with patch("app.api.employee.NotificationService.send_notification", new=AsyncMock(return_value=None)):
                response = asyncio.run(upload_leave_excel(request=request, file=upload, db=MagicMock()))
                assert response.message == "Leave data imported successfully"
                assert response.data["processed"] == 1

