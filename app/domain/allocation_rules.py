"""Pure allocation validation rules (legacy AllocationsService parity)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum

MAX_ALLOCATION_HOURS_PER_DAY = 8
BENCH_PROJECT_CODE = "BENCH"
OPEN_END_HORIZON_YEARS = 3


class AllocationType(StrEnum):
    STAFFING = "STAFFING"
    DEPLOYABLE = "DEPLOYABLE"
    NONDEPLOYABLE = "NONDEPLOYABLE"
    LOCKED = "LOCKED"
    NONBILLABLE = "NONBILLABLE"


class ProjectType(StrEnum):
    IN_HOUSE = "IN_HOUSE"
    STAFFING = "STAFFING"
    PRODUCT = "PRODUCT"


class AllocationRuleError(Exception):
    """Business rule violation; map to HTTP 400 in the API layer."""


def as_date(value: date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def open_end_effective_date(today: date | None = None) -> date:
    base = today or date.today()
    return base.replace(year=base.year + OPEN_END_HORIZON_YEARS)


def validate_date_window(start: date, end: date | None) -> None:
    if end is not None and not start < end:
        raise AllocationRuleError("End date must be after the start date")


def validate_allocated_hours(hours: int) -> None:
    if hours < 1 or hours > MAX_ALLOCATION_HOURS_PER_DAY:
        raise AllocationRuleError(
            f"allocated_hours must be between 1 and {MAX_ALLOCATION_HOURS_PER_DAY}, got {hours}"
        )


def validate_allocation_type_for_project(allocation_type: AllocationType | str, project_type: str) -> None:
    at = AllocationType(allocation_type) if isinstance(allocation_type, str) else allocation_type
    try:
        pt = ProjectType(project_type)
    except ValueError:
        return
    if at == AllocationType.STAFFING and pt != ProjectType.STAFFING:
        raise AllocationRuleError("STAFFING allocation type is only allowed for STAFFING project types")


def validate_locked_in_date(
    start: date,
    end: date | None,
    locked_in: date | None,
    allocation_type: AllocationType | str,
) -> None:
    at = AllocationType(allocation_type) if isinstance(allocation_type, str) else allocation_type
    if at == AllocationType.LOCKED:
        if locked_in is None:
            raise AllocationRuleError("Locked-in date is required for LOCKED allocation type")
        li = locked_in
        if li < start:
            raise AllocationRuleError("Locked-in date must be between allocation start and end date")
        if end is not None and li > end:
            raise AllocationRuleError("Locked-in date must be between allocation start and end date")
    elif locked_in is not None:
        raise AllocationRuleError("locked_in_date is only allowed when allocation_type is LOCKED")


def validate_staffing_project_allocation_type(new_allocation_type: AllocationType | str, project_type: str) -> None:
    """When the project is STAFFING, only STAFFING or LOCKED allocation types are allowed (legacy update rule)."""
    try:
        pt = ProjectType(project_type)
    except ValueError:
        return
    if pt != ProjectType.STAFFING:
        return
    at = AllocationType(new_allocation_type) if isinstance(new_allocation_type, str) else new_allocation_type
    if at not in (AllocationType.STAFFING, AllocationType.LOCKED):
        raise AllocationRuleError("STAFFING projects can hold only STAFFING and LOCKED allocations")


def max_daily_hours_non_bench(
    allocations: list[object],
    day: date,
    *,
    open_end_cap: date | None = None,
) -> int:
    cap = open_end_cap or open_end_effective_date()
    total = 0
    for a in allocations:
        if not getattr(a, "isActive", True):
            continue
        code = getattr(a, "project_code", None)
        if code is None:
            try:
                code = getattr(a, "projectCode", None)
            except Exception:
                code = None
        if code == BENCH_PROJECT_CODE:
            continue
        s = as_date(getattr(a, "startDate", None) or getattr(a, "start_date", None))
        if s is None:
            continue
        raw_end = getattr(a, "endDate", None) or getattr(a, "end_date", None)
        e_date = as_date(raw_end) if raw_end is not None else cap
        if s <= day <= e_date:
            total += int(getattr(a, "allocatedHours", None) or getattr(a, "allocated_hours", 0))
    return total


def compute_max_existing_hours_in_range(
    allocations: list[object],
    range_start: date,
    range_end: date,
    *,
    open_end_cap: date | None = None,
) -> int:
    """Maximum total non-bench hours on any single calendar day in [range_start, range_end]."""
    if range_end < range_start:
        return 0
    cap = open_end_cap or open_end_effective_date()
    max_h = 0
    d = range_start
    while d <= range_end:
        max_h = max(max_h, max_daily_hours_non_bench(allocations, d, open_end_cap=cap))
        d += timedelta(days=1)
    return max_h


def assert_new_allocation_fits_daily_cap(
    existing_non_bench_allocations: list[object],
    range_start: date,
    range_end: date | None,
    requested_hours: int,
    *,
    open_end_cap: date | None = None,
) -> None:
    """Legacy computeAllocation: max day load + new hours must not exceed 8."""
    validate_allocated_hours(requested_hours)
    end = range_end if range_end is not None else open_end_effective_date(today=range_start)
    max_existing = compute_max_existing_hours_in_range(
        existing_non_bench_allocations, range_start, end, open_end_cap=open_end_cap
    )
    remaining = MAX_ALLOCATION_HOURS_PER_DAY - max_existing
    if remaining < requested_hours:
        raise AllocationRuleError(
            f"No sufficient hours to allocate - Only {remaining} hours can be allocated"
        )
