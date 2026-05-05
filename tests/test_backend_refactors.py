import asyncio
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.project import get_all_projects
from app.api.role import assign_role
from app.schemas.role import AssignRoleRequest, AssignRoleResponse
from app.services.project_service import ProjectService
from app.services.reference_service import ReferenceService
from app.services.user_request_service import UserRequestService


def _request(path: str = "/x", headers: dict[str, str] | None = None) -> Request:
    hdrs = []
    for key, value in (headers or {}).items():
        hdrs.append((key.lower().encode(), value.encode()))
    return Request({"type": "http", "method": "GET", "path": path, "headers": hdrs})


def test_manager_list_hides_self_requests() -> None:
    service = object.__new__(UserRequestService)
    actor = SimpleNamespace(id=101, email="manager@webknot.in")
    service._get_user_by_email_or_404 = lambda _email: _async_return(actor)  # type: ignore[method-assign]
    own_row = SimpleNamespace(
        id=1,
        user_id=101,
        user=SimpleNamespace(email="manager@webknot.in"),
        request_from_date=date(2026, 5, 1),
        request_to_date=date(2026, 5, 1),
        comments=None,
        request_type="LEAVE",
        status="PENDING",
        is_half_day=False,
        reference_file_url=None,
        created_at=date(2026, 5, 1),
        updated_at=date(2026, 5, 1),
    )
    other_row = SimpleNamespace(
        id=2,
        user_id=202,
        user=SimpleNamespace(email="employee@webknot.in"),
        request_from_date=date(2026, 5, 1),
        request_to_date=date(2026, 5, 1),
        comments=None,
        request_type="LEAVE",
        status="PENDING",
        is_half_day=False,
        reference_file_url=None,
        created_at=date(2026, 5, 1),
        updated_at=date(2026, 5, 1),
    )
    service.request_repo = SimpleNamespace(
        list_for_manager_scope=lambda **_kwargs: _async_return(([own_row, other_row], 2))
    )
    response = asyncio.run(
        service.list_requests(
            actor_email="manager@webknot.in",
            actor_roles={"ROLE_MANAGER"},
            from_date=date(2026, 5, 1),
            to_date=date(2026, 5, 31),
            request_type="LEAVE",
            page=0,
            size=10,
        )
    )
    assert response.total_elements == 1
    assert len(response.data) == 1
    assert response.data[0].emp_email == "employee@webknot.in"


def test_reference_service_lists_unique_departments() -> None:
    service = object.__new__(ReferenceService)
    service.designations = SimpleNamespace(
        list_unique_departments=lambda: _async_return(["AI/ML", "DevOps", "Finance"])
    )
    rows = asyncio.run(service.list_departments())
    assert [row.name for row in rows] == ["AI/ML", "DevOps", "Finance"]


def test_project_service_project_assigned_to_user_returns_role_hours_and_start_date() -> None:
    service = object.__new__(ProjectService)
    service.repo = SimpleNamespace(
        get_user_by_email=lambda _email: _async_return(SimpleNamespace(id=9)),
        get_active_allocations_for_user=lambda _id: _async_return(
            [
                SimpleNamespace(projectCode="P1", role="Tech Lead", allocatedHours=6, startDate=date(2026, 5, 1)),
                SimpleNamespace(projectCode="BENCH", role="bench", allocatedHours=2, startDate=date(2026, 5, 1)),
            ]
        ),
        get_projects_by_codes=lambda _codes: _async_return([SimpleNamespace(projectCode="P1", projectName="Phoenix")]),
    )
    rows = asyncio.run(service.get_project_codes_for_user("user@webknot.in"))
    assert len(rows) == 1
    assert rows[0].project_code == "P1"
    assert rows[0].project_name == "Phoenix"
    assert rows[0].role == "Tech Lead"
    assert rows[0].allocated_hours == 6
    assert rows[0].start_date == date(2026, 5, 1)


def test_projects_endpoint_allows_admin(monkeypatch) -> None:
    class _FakeTool:
        def __init__(self, _db):
            pass

        async def get_all_projects(self, page: int, size: int, search: str | None):
            _ = (page, size, search)
            return SimpleNamespace(model_dump=lambda: {"items": [], "total": 0, "page": 0, "size": 10})

    monkeypatch.setattr("app.api.project.ProjectTool", _FakeTool)
    request = _request("/api/v1/projects", headers={"cookie": "roles=ROLE_ADMIN"})
    response = asyncio.run(get_all_projects(request=request, page=0, size=10, search=None, db=object()))
    assert response.message == "success"


def test_roles_assign_blocks_non_hr_admin_without_bootstrap() -> None:
    request = _request("/api/v1/roles/assign", headers={"cookie": "email=u@x.com; roles=ROLE_EMPLOYEE"})
    with pytest.raises(HTTPException) as err:
        asyncio.run(
            assign_role(
                payload=AssignRoleRequest(target_email="target@webknot.in", role="ROLE_HR"),
                request=request,
                x_admin_bootstrap_key=None,
                db=object(),
            )
        )
    assert err.value.status_code == 403


def test_roles_assign_allows_bootstrap_without_actor(monkeypatch) -> None:
    class _FakeTool:
        def __init__(self, _db):
            pass

        async def assign_role(self, **_kwargs):
            return AssignRoleResponse(
                target_email="target@webknot.in",
                assigned_role="ROLE_HR",
                assigned_by="anonymous",
                message="Role assigned successfully",
            )

    monkeypatch.setattr("app.api.role.RoleTool", _FakeTool)
    monkeypatch.setattr("app.api.role.get_settings", lambda: SimpleNamespace(admin_bootstrap_key="secret"))
    request = _request("/api/v1/roles/assign")
    response = asyncio.run(
        assign_role(
            payload=AssignRoleRequest(target_email="target@webknot.in", role="ROLE_HR"),
            request=request,
            x_admin_bootstrap_key="secret",
            db=object(),
        )
    )
    assert response.assigned_role == "ROLE_HR"


def _async_return(value):
    async def _inner(*_args, **_kwargs):
        return value

    return _inner()
