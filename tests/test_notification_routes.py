import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.api.notification import (
    create_announcement,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    subscribe_notifications,
)
from app.schemas.notification import AnnouncementCreateRequest


def _request(path: str, method: str = "GET", headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {"type": "http", "method": method, "path": path, "headers": hdrs}
    return Request(scope)


def test_list_notifications_success() -> None:
    request = _request("/api/v1/notifications", headers={"cookie": "roles=ROLE_EMPLOYEE; email=u@x.com"})
    fake = {"current_page": 0, "total_pages": 0, "page_size": 20, "total_elements": 0, "data": []}
    with patch("app.api.notification.NotificationService.list_notifications_for_actor", new=AsyncMock(return_value=fake)):
        response = asyncio.run(list_notifications(request=request, db=MagicMock()))
        assert response.message == "success"
        assert response.data["total_elements"] == 0


def test_mark_read_and_mark_all_read_success() -> None:
    request = _request("/api/v1/notifications/1/read", method="PUT", headers={"cookie": "roles=ROLE_EMPLOYEE; email=u@x.com"})
    fake_row = {
        "id": 1,
        "receiver_id": 1,
        "sender_id": 2,
        "type": "LEAVE_REQUEST",
        "title": "x",
        "message": "y",
        "is_read": True,
        "created_at": "2026-01-01T00:00:00",
    }
    with patch("app.api.notification.NotificationService.mark_read_for_actor", new=AsyncMock(return_value=fake_row)):
        response = asyncio.run(mark_notification_read(notification_id=1, request=request, db=MagicMock()))
        assert response.data["is_read"] is True
    with patch("app.api.notification.NotificationService.mark_all_read_for_actor", new=AsyncMock(return_value=4)):
        response = asyncio.run(mark_all_notifications_read(request=request, db=MagicMock()))
        assert response.data["updated"] == 4


def test_announcement_requires_hr_admin() -> None:
    request = _request("/api/v1/notifications/announcement", method="POST", headers={"cookie": "roles=ROLE_EMPLOYEE; email=u@x.com"})
    payload = AnnouncementCreateRequest(title="t", message="m")
    try:
        asyncio.run(create_announcement(payload=payload, request=request, db=MagicMock()))
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 403


def test_subscribe_notifications_returns_stream() -> None:
    request = _request("/api/v1/notifications/subscribe", headers={"cookie": "roles=ROLE_EMPLOYEE; email=u@x.com"})
    with patch("app.api.notification.UserRepository.get_by_email", new=AsyncMock(return_value=type("U", (), {"id": 7})())):
        response = asyncio.run(subscribe_notifications(request=request, db=MagicMock()))
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"

