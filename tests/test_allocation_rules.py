from datetime import date, datetime, time

import pytest
from pydantic import ValidationError

from app.domain.allocation_rules import (
    AllocationRuleError,
    AllocationType,
    assert_new_allocation_fits_daily_cap,
    compute_max_existing_hours_in_range,
    max_daily_hours_non_bench,
    validate_allocated_hours,
    validate_allocation_type_for_project,
    validate_date_window,
    validate_locked_in_date,
    validate_staffing_project_allocation_type,
)
from app.schemas.allocation import AllocationCreateRequest


class _Alloc:
    def __init__(
        self,
        *,
        start: date,
        end: date | None,
        hours: int,
        project_code: str = "PROJ1",
        is_active: bool = True,
    ) -> None:
        self.startDate = datetime.combine(start, time.min)
        self.endDate = datetime.combine(end, time.min) if end else None
        self.allocatedHours = hours
        self.projectCode = project_code
        self.isActive = is_active


def test_validate_date_window_rejects_equal_or_reversed() -> None:
    d0 = date(2025, 1, 1)
    with pytest.raises(AllocationRuleError, match="End date"):
        validate_date_window(d0, d0)
    with pytest.raises(AllocationRuleError, match="End date"):
        validate_date_window(date(2025, 2, 1), d0)


def test_validate_allocated_hours_bounds() -> None:
    with pytest.raises(AllocationRuleError):
        validate_allocated_hours(0)
    with pytest.raises(AllocationRuleError):
        validate_allocated_hours(9)
    validate_allocated_hours(8)


def test_staffing_type_requires_staffing_project() -> None:
    with pytest.raises(AllocationRuleError, match="STAFFING"):
        validate_allocation_type_for_project(AllocationType.STAFFING, "IN_HOUSE")
    validate_allocation_type_for_project(AllocationType.STAFFING, "STAFFING")


def test_locked_requires_locked_in_and_bounds() -> None:
    s, e = date(2025, 1, 1), date(2025, 12, 31)
    with pytest.raises(AllocationRuleError, match="required"):
        validate_locked_in_date(s, e, None, AllocationType.LOCKED)
    with pytest.raises(AllocationRuleError, match="between"):
        validate_locked_in_date(s, e, date(2024, 6, 1), AllocationType.LOCKED)
    validate_locked_in_date(s, e, date(2025, 6, 1), AllocationType.LOCKED)


def test_non_locked_rejects_locked_in() -> None:
    with pytest.raises(AllocationRuleError, match="only allowed"):
        validate_locked_in_date(date(2025, 1, 1), None, date(2025, 2, 1), AllocationType.DEPLOYABLE)


def test_staffing_project_allocation_types() -> None:
    with pytest.raises(AllocationRuleError, match="STAFFING projects"):
        validate_staffing_project_allocation_type(AllocationType.DEPLOYABLE, "STAFFING")
    validate_staffing_project_allocation_type(AllocationType.STAFFING, "STAFFING")
    validate_staffing_project_allocation_type(AllocationType.LOCKED, "STAFFING")


def test_max_daily_hours_non_bench_ignores_bench_and_inactive() -> None:
    day = date(2025, 6, 15)
    allocs = [
        _Alloc(start=date(2025, 6, 1), end=date(2025, 6, 30), hours=4, project_code="BENCH"),
        _Alloc(start=date(2025, 6, 1), end=date(2025, 6, 30), hours=5, project_code="P1"),
        _Alloc(start=date(2025, 6, 1), end=date(2025, 6, 30), hours=6, project_code="P2", is_active=False),
    ]
    assert max_daily_hours_non_bench(allocs, day) == 5


def test_daily_cap_fails_when_overbooked() -> None:
    day = date(2025, 6, 15)
    existing = [_Alloc(start=date(2025, 6, 1), end=date(2025, 6, 30), hours=6, project_code="P1")]
    with pytest.raises(AllocationRuleError, match="Only 2 hours"):
        assert_new_allocation_fits_daily_cap(existing, day, day, 3)


def test_daily_cap_passes_when_room() -> None:
    day = date(2025, 6, 15)
    existing = [_Alloc(start=date(2025, 6, 1), end=date(2025, 6, 30), hours=5, project_code="P1")]
    assert_new_allocation_fits_daily_cap(existing, day, day, 3)


def test_compute_max_in_range() -> None:
    existing = [
        _Alloc(start=date(2025, 6, 10), end=date(2025, 6, 12), hours=6, project_code="P1"),
        _Alloc(start=date(2025, 6, 11), end=date(2025, 6, 11), hours=4, project_code="P2"),
    ]
    # June 11: 6+4=10
    m = compute_max_existing_hours_in_range(existing, date(2025, 6, 10), date(2025, 6, 12))
    assert m == 10


def test_allocation_create_request_schema() -> None:
    m = AllocationCreateRequest(
        employee_email="a@b.co",
        project_code="  abc  ",
        allocated_hours=4,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 2, 1),
        allocation_type=AllocationType.DEPLOYABLE,
    )
    assert m.project_code == "ABC"


def test_allocation_create_request_billing_status_alias_and_normalization() -> None:
    m = AllocationCreateRequest(
        employeeEmail="a@b.co",
        projectCode="abc",
        allocatedHours=4,
        startDate=date(2025, 1, 1),
        endDate=date(2025, 2, 1),
        allocationType=AllocationType.DEPLOYABLE,
        billingStatus="billed",
    )
    assert m.billing_status == "BILLED"


def test_allocation_create_request_rejects_invalid_billing_status() -> None:
    with pytest.raises(ValidationError):
        AllocationCreateRequest(
            employee_email="a@b.co",
            project_code="ABC",
            allocated_hours=4,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 2, 1),
            allocation_type=AllocationType.DEPLOYABLE,
            billing_status="UNBILLED",
        )
