import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.access import require_any_role


class _Settings:
    enable_role_checks = True


def _request_with_roles_cookie(roles: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"cookie", f"roles={roles}".encode("utf-8"))],
    }
    return Request(scope)


def test_require_any_role_blocks_non_hr(monkeypatch) -> None:
    monkeypatch.setattr("app.api.access.get_settings", lambda: _Settings())
    request = _request_with_roles_cookie("ROLE_EMPLOYEE")
    with pytest.raises(HTTPException):
        require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})


def test_require_any_role_allows_hr(monkeypatch) -> None:
    monkeypatch.setattr("app.api.access.get_settings", lambda: _Settings())
    request = _request_with_roles_cookie("ROLE_HR")
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
