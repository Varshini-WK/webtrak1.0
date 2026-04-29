from datetime import date
from unittest.mock import MagicMock

from fastapi import HTTPException

from app.services.employee_service import EmployeeService


def test_validate_primary_skills_requires_non_blank() -> None:
    service = EmployeeService(MagicMock())
    try:
        service._validate_primary_skills(["", "  "])  # noqa: SLF001
        raise AssertionError("Expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Primary Skill" in str(exc.detail)


def test_initial_leave_balance_for_intern_is_zero() -> None:
    service = EmployeeService(MagicMock())
    primary, secondary = service._initial_leave_balance("INTERN", date.today())  # noqa: SLF001
    assert primary == 0.0
    assert secondary == 0.0


def test_initial_leave_balance_for_fulltime_depends_on_doj_first_half_before_august() -> None:
    service = EmployeeService(MagicMock())
    primary, secondary = service._initial_leave_balance("FULLTIME", date(2026, 4, 1))  # noqa: SLF001
    assert primary == 1.5
    assert secondary == 0.0


def test_initial_leave_balance_for_fulltime_depends_on_doj_first_half_august_onwards() -> None:
    service = EmployeeService(MagicMock())
    primary, secondary = service._initial_leave_balance("FULLTIME", date(2026, 9, 1))  # noqa: SLF001
    assert primary == 0.0
    assert secondary == 1.5


def test_initial_leave_balance_for_fulltime_second_half_month_is_zero() -> None:
    service = EmployeeService(MagicMock())
    primary, secondary = service._initial_leave_balance("FULLTIME", date(2026, 4, 16))  # noqa: SLF001
    assert primary == 0.0
    assert secondary == 0.0
