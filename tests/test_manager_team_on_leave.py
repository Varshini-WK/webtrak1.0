"""Unit tests for manager team-on-leave aggregation (no DB)."""

import asyncio
from datetime import date
from types import SimpleNamespace

from app.services.project_service import ProjectService


def _async_return(value):
    async def _inner():
        return value

    return _inner()


def test_manager_team_on_leave_filters_deduct_and_excludes_manager() -> None:
    service = object.__new__(ProjectService)
    mgr = SimpleNamespace(id=1, email="mgr@x.com", name="Mgr")
    emp = SimpleNamespace(id=2, email="e@x.com", name="Emp", emp_id="E1", empId="E1")

    service.repo = SimpleNamespace(
        get_user_by_email=lambda _e: _async_return(mgr),
        get_manager_project_codes=lambda _mid: _async_return(["PROJ_A"]),
        get_projects_by_codes=lambda _codes: _async_return(
            [SimpleNamespace(projectCode="PROJ_A", projectName="Project A")]
        ),
    )
    service.alloc_repo = SimpleNamespace(
        list_user_project_pairs_for_projects_on_date=lambda _codes, _d: _async_return(
            [(1, "PROJ_A"), (2, "PROJ_A")]
        )
    )
    service.leave_tx_repo = SimpleNamespace(
        list_deducts_for_user_ids_date_range=lambda uids, _f, _t: _async_return([(2, date(2026, 6, 2), 1.0)])
    )
    service.user_repo = SimpleNamespace(list_by_ids=lambda _ids: _async_return([emp]))

    out = asyncio.run(service.get_manager_team_on_leave_today("mgr@x.com", date(2026, 6, 2)))
    assert out.as_of_date == date(2026, 6, 2)
    assert len(out.team_on_leave) == 1
    row = out.team_on_leave[0]
    assert row.user_id == 2
    assert row.leave_units_today == 1.0
    assert len(row.projects) == 1
    assert row.projects[0].project_code == "PROJ_A"


def test_manager_team_on_leave_empty_when_no_deduct() -> None:
    service = object.__new__(ProjectService)
    mgr = SimpleNamespace(id=1, email="mgr@x.com", name="Mgr")
    service.repo = SimpleNamespace(
        get_user_by_email=lambda _e: _async_return(mgr),
        get_manager_project_codes=lambda _mid: _async_return(["PROJ_A"]),
        get_projects_by_codes=lambda _codes: _async_return([]),
    )
    service.alloc_repo = SimpleNamespace(
        list_user_project_pairs_for_projects_on_date=lambda _codes, _d: _async_return([(2, "PROJ_A")])
    )
    service.leave_tx_repo = SimpleNamespace(
        list_deducts_for_user_ids_date_range=lambda uids, _f, _t: _async_return([])
    )

    out = asyncio.run(service.get_manager_team_on_leave_today("mgr@x.com", date(2026, 6, 2)))
    assert out.team_on_leave == []
