from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from app.api.access import get_actor_email, get_actor_roles, require_any_role
from app.core.security import create_access_token


def _request(headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode("latin-1"), value.encode("latin-1")))
    scope = {"type": "http", "method": "GET", "path": "/", "headers": hdrs}
    return Request(scope)


def test_get_actor_email_from_cookie() -> None:
    request = _request(headers={"cookie": "email=cookie.user@webknot.in; roles=ROLE_EMPLOYEE"})
    assert get_actor_email(request) == "cookie.user@webknot.in"


def test_get_actor_email_from_bearer_when_cookie_missing() -> None:
    token = create_access_token(
        subject="bearer.user@webknot.in",
        roles=["ROLE_HR"],
        status="ACTIVE",
        user_type="FULLTIME",
    )
    request = _request(headers={"authorization": f"Bearer {token}"})
    assert get_actor_email(request) == "bearer.user@webknot.in"


def test_cookie_precedence_when_cookie_and_bearer_both_present() -> None:
    token = create_access_token(
        subject="bearer.user@webknot.in",
        roles=["ROLE_HR"],
        status="ACTIVE",
        user_type="FULLTIME",
    )
    request = _request(
        headers={
            "cookie": "email=cookie.user@webknot.in; roles=ROLE_EMPLOYEE",
            "authorization": f"Bearer {token}",
        }
    )
    assert get_actor_email(request) == "cookie.user@webknot.in"
    assert get_actor_roles(request) == {"ROLE_EMPLOYEE"}


def test_invalid_bearer_does_not_override_valid_cookie() -> None:
    request = _request(
        headers={
            "cookie": "email=cookie.user@webknot.in; roles=ROLE_HR",
            "authorization": "Bearer not-a-valid-token",
        }
    )
    assert get_actor_email(request) == "cookie.user@webknot.in"
    assert get_actor_roles(request) == {"ROLE_HR"}


def test_get_actor_email_unauthorized_when_no_cookie_or_valid_bearer() -> None:
    request = _request(headers={"authorization": "Bearer invalid"})
    try:
        get_actor_email(request)
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 401
        assert exc.detail == "Unauthorized"


def test_require_any_role_accepts_bearer_only_roles() -> None:
    token = create_access_token(
        subject="bearer.hr@webknot.in",
        roles=["ROLE_HR"],
        status="ACTIVE",
        user_type="FULLTIME",
    )
    request = _request(headers={"authorization": f"Bearer {token}"})
    require_any_role(request, {"ROLE_HR"})


def test_require_any_role_denies_role_mismatch() -> None:
    token = create_access_token(
        subject="bearer.employee@webknot.in",
        roles=["ROLE_EMPLOYEE"],
        status="ACTIVE",
        user_type="FULLTIME",
    )
    request = _request(headers={"authorization": f"Bearer {token}"})
    try:
        require_any_role(request, {"ROLE_ADMIN"})
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Insufficient role"


def test_require_any_role_skips_checks_when_disabled() -> None:
    request = _request()
    with patch("app.api.access.get_settings") as mock_get_settings:
        mock_get_settings.return_value = type("Settings", (), {"enable_role_checks": False})()
        require_any_role(request, {"ROLE_ADMIN"})
