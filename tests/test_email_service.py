import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api import scheduler as scheduler_api
from app.domain.email_templates import ONBOARD_INVITE
from app.domain.message_constants import ONBOARD_INVITE_SUBJECT, NO_TIME_LOGS_SUBJECT
from app.services.email_service import EmailService
from app.services.employee_service import EmployeeService


def _request(*, path: str, method: str, headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {"type": "http", "method": method, "path": path, "headers": hdrs}
    return Request(scope)


def test_email_service_nonprod_overrides_to_and_cc() -> None:
    settings = SimpleNamespace(
        app_env="dev",
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        smtp_use_tls=True,
        smtp_sender="sender@example.com",
    )
    service = EmailService(settings=settings)  # type: ignore[arg-type]

    server = MagicMock()
    server.starttls = MagicMock()
    server.login = MagicMock()
    server.sendmail = MagicMock()
    server.quit = MagicMock()

    with patch("app.services.email_service.smtplib.SMTP", return_value=server):
        asyncio.run(service.send_simple_email("user@example.com", "subj", "body", "cc@example.com"))

    # Recipient override should route to sender only.
    sendmail_args = server.sendmail.call_args.args
    assert sendmail_args[0] == "sender@example.com"
    assert sendmail_args[1] == ["sender@example.com"]
    msg_string = sendmail_args[2]
    assert "Content-Type: text/plain" in msg_string


def test_email_service_html_sets_content_type() -> None:
    settings = SimpleNamespace(
        app_env="prod",
        smtp_host="smtp.example.test",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        smtp_use_tls=True,
        smtp_sender="sender@example.com",
    )
    service = EmailService(settings=settings)  # type: ignore[arg-type]

    server = MagicMock()
    server.starttls = MagicMock()
    server.login = MagicMock()
    server.sendmail = MagicMock()
    server.quit = MagicMock()

    with patch("app.services.email_service.smtplib.SMTP", return_value=server):
        asyncio.run(service.send_email("to@example.com", "subj", "<b>hi</b>", cc=None, is_html=True))

    sendmail_args = server.sendmail.call_args.args
    assert sendmail_args[0] == "sender@example.com"
    assert sendmail_args[1] == ["to@example.com"]
    msg_string = sendmail_args[2]
    assert "Content-Type: text/html" in msg_string


def test_employee_onboarding_invite_calls_send_email_html() -> None:
    service = object.__new__(EmployeeService)
    service.email_service = AsyncMock()

    asyncio.run(service._send_onboarding_invite("user@example.com", "Alice"))

    expected_body = ONBOARD_INVITE % "Alice"
    service.email_service.send_email.assert_awaited_once()
    _, kwargs = service.email_service.send_email.await_args
    assert kwargs["to"] == "user@example.com"
    assert kwargs["subject"] == ONBOARD_INVITE_SUBJECT
    assert kwargs["body"] == expected_body
    assert kwargs["cc"] is None
    assert kwargs["is_html"] is True


def test_scheduler_notify_timelogs_admin_endpoint_calls_job() -> None:
    with patch.object(scheduler_api, "get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(app_env="dev", admin_bootstrap_key="admin-pass")
        with patch(
            "app.api.scheduler.ScheduledJobsService.send_timelog_defaults_notifications",
            new=AsyncMock(return_value=0),
        ):
            req = _request(
                path="/api/v1/notify/timelogs/",
                method="GET",
                headers={
                    "cookie": "roles=ROLE_ADMIN",
                    "Authorization": "admin-pass",
                },
            )
            resp = asyncio.run(scheduler_api.send_timelogs_notification(req, db=MagicMock()))
            assert resp.message == "success"


def test_scheduler_secret_code_user_not_found_returns_message() -> None:
    with patch.object(scheduler_api, "get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(app_env="dev", admin_bootstrap_key="admin-pass")
        with patch("app.api.scheduler.UserRepository.get_by_email", new=AsyncMock(return_value=None)):
            req = _request(
                path="/api/v1/secret-code/user@example.com",
                method="GET",
                headers={
                    "cookie": "roles=ROLE_ADMIN",
                    "Authorization": "admin-pass",
                },
            )
            resp = asyncio.run(scheduler_api.send_secret_code_email("user@example.com", req, db=MagicMock()))
            assert resp.status_code == 400
            payload = resp.body.decode("utf-8")
            assert "User not found" in payload


def test_scheduler_secret_code_success_calls_email() -> None:
    user = SimpleNamespace(email="user@example.com")
    with patch.object(scheduler_api, "get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(app_env="dev", admin_bootstrap_key="admin-pass")
        with patch("app.api.scheduler.UserRepository.get_by_email", new=AsyncMock(return_value=user)):
            with patch("app.api.scheduler.EmailService.send_simple_email", new=AsyncMock()) as send_mock:
                req = _request(
                    path="/api/v1/secret-code/user@example.com",
                    method="GET",
                    headers={
                        "cookie": "roles=ROLE_ADMIN",
                        "Authorization": "admin-pass",
                    },
                )
                asyncio.run(scheduler_api.send_secret_code_email("user@example.com", req, db=MagicMock()))
                send_mock.assert_awaited_once()
                _, kwargs = send_mock.await_args
                assert kwargs["to"] == "user@example.com"

