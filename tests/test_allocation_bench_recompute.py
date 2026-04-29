from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.services.allocation_service import AllocationService


def _mk_allocation(
    *,
    allocation_id: int,
    project_code: str,
    allocated_hours: int,
    start_date: date,
    end_date: date | None = None,
    is_active: bool = True,
):
    return SimpleNamespace(
        id=allocation_id,
        projectCode=project_code,
        allocatedHours=allocated_hours,
        startDate=datetime(start_date.year, start_date.month, start_date.day),
        endDate=datetime(end_date.year, end_date.month, end_date.day) if end_date else None,
        isActive=is_active,
    )


def test_recompute_bench_creates_remaining_hours_from_non_bench_allocations() -> None:
    svc = AllocationService(MagicMock())
    svc.alloc_repo.get_active_bench_for_user = AsyncMock(return_value=[])
    non_bench = [
        _mk_allocation(
            allocation_id=10,
            project_code="P001",
            allocated_hours=5,
            start_date=date.today(),
        )
    ]
    svc.alloc_repo.get_active_non_bench_for_user = AsyncMock(return_value=non_bench)
    svc.alloc_repo.create = AsyncMock()
    svc.alloc_repo.deactivate = AsyncMock()

    import asyncio

    asyncio.run(svc.recompute_bench_for_user(user_id=42, bench_role="Developer", client=MagicMock()))

    created_payload = svc.alloc_repo.create.await_args.args[0]
    assert created_payload["projectCode"] == "BENCH"
    assert created_payload["allocatedHours"] == 3
    assert created_payload["isActive"] is True


def test_recompute_bench_creates_full_eight_when_no_non_bench() -> None:
    svc = AllocationService(MagicMock())
    svc.alloc_repo.get_active_bench_for_user = AsyncMock(return_value=[])
    svc.alloc_repo.get_active_non_bench_for_user = AsyncMock(return_value=[])
    svc.alloc_repo.create = AsyncMock()
    svc.alloc_repo.deactivate = AsyncMock()

    import asyncio

    asyncio.run(svc.recompute_bench_for_user(user_id=77, bench_role="bench", client=MagicMock()))

    created_payload = svc.alloc_repo.create.await_args.args[0]
    assert created_payload["projectCode"] == "BENCH"
    assert created_payload["allocatedHours"] == 8
