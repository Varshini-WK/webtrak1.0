from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.db_insert import _seed_kpi_definitions
from app.services.reference_service import ReferenceService


def test_create_kpi_definition_uses_designation_in_duplicate_check_and_payload() -> None:
    service = ReferenceService(MagicMock())
    service._get_band = AsyncMock(return_value=object())
    service.kpis.exists_duplicate = AsyncMock(return_value=False)
    created = MagicMock()
    created.id = 1
    created.band_id = 7
    created.department = "Developer"
    created.designation = "Tech Lead"
    created.kpi_name = "Code Quality"
    created.weightage = Decimal("40")
    created.active = True
    created.created_at = created.updated_at = "2026-04-16T00:00:00Z"
    service.kpis.create = AsyncMock(return_value=created)

    payload = MagicMock(
        band_id=7,
        department=MagicMock(value="Developer"),
        designation="Tech Lead",
        kpi_name="Code Quality",
        weightage=Decimal("40"),
        active=True,
    )

    import asyncio

    asyncio.run(service.create_kpi_definition(payload))

    service.kpis.exists_duplicate.assert_awaited_once_with(7, "Developer", "Tech Lead", "Code Quality")
    service.kpis.create.assert_awaited_once()
    data = service.kpis.create.await_args.args[0]
    assert data["designation"] == "Tech Lead"


def test_update_kpi_definition_uses_designation_in_duplicate_check() -> None:
    service = ReferenceService(MagicMock())
    existing = MagicMock(
        band_id=5,
        department="Developer",
        designation="Tech Lead",
        kpi_name="Code Quality",
        weightage=Decimal("40"),
        active=True,
    )
    service.kpis.get_by_id = AsyncMock(return_value=existing)
    service._get_band = AsyncMock(return_value=object())
    service.kpis.exists_duplicate = AsyncMock(return_value=False)
    updated = MagicMock()
    updated.id = 10
    updated.band_id = 5
    updated.department = "Developer"
    updated.designation = "Sr. Tech Lead"
    updated.kpi_name = "Code Quality"
    updated.weightage = Decimal("30")
    updated.active = True
    updated.created_at = updated.updated_at = "2026-04-16T00:00:00Z"
    service.kpis.update = AsyncMock(return_value=updated)

    payload = MagicMock(
        band_id=None,
        department=None,
        designation="Sr. Tech Lead",
        kpi_name=None,
        weightage=Decimal("30"),
        active=None,
    )

    import asyncio

    asyncio.run(service.update_kpi_definition(10, payload))

    service.kpis.exists_duplicate.assert_awaited_once_with(
        5,
        "Developer",
        "Sr. Tech Lead",
        "Code Quality",
        exclude_id=10,
    )


def test_seed_kpi_definitions_skips_when_any_rows_exist() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=1)

    class _Tx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    database = MagicMock()
    database.tx = MagicMock(return_value=_Tx())

    import asyncio

    asyncio.run(_seed_kpi_definitions(database))

    session.add.assert_not_called()
