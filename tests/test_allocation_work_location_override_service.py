import asyncio
from datetime import date
from types import SimpleNamespace

from app.domain.allocation_rules import AllocationType
from app.schemas.allocation import AllocationCreateRequest
from app.services.allocation_service import AllocationService


class _FakeAllocRepo:
    def __init__(self):
        self.create_payloads: list[dict] = []

    async def create(self, data: dict, client=None):
        _ = client
        self.create_payloads.append(dict(data))
        return SimpleNamespace(id=101)


class _FakeEmployeeRepo:
    def __init__(self):
        self.update_calls: list[tuple[int, dict]] = []

    async def update_user(self, user_id: int, data: dict, client=None):
        _ = client
        self.update_calls.append((user_id, dict(data)))
        return SimpleNamespace(id=user_id)


def test_write_new_allocation_syncs_user_work_location_type():
    async def _run():
        service = AllocationService(db=SimpleNamespace())
        service.alloc_repo = _FakeAllocRepo()
        service.employee_repo = _FakeEmployeeRepo()

        async def _noop(*args, **kwargs):
            return None

        service.recompute_bench_for_user = _noop

        payload = AllocationCreateRequest(
            employee_email="member@example.com",
            project_code="ABC",
            allocated_hours=8,
            start_date=date(2026, 4, 27),
            end_date=None,
            allocation_type=AllocationType.DEPLOYABLE,
            billing_status="BUFFER",
            work_location_type="REMOTE",
            role=None,
        )
        row = await service._write_new_allocation(
            user_id=55,
            project_code="ABC",
            payload=payload,
            client=SimpleNamespace(),
        )

        assert row.id == 101
        assert service.alloc_repo.create_payloads[0]["billingStatus"] == "BUFFER"
        assert service.alloc_repo.create_payloads[0]["workLocationType"] == "REMOTE"
        assert service.employee_repo.update_calls == [(55, {"workLocationType": "REMOTE"})]

    asyncio.run(_run())
