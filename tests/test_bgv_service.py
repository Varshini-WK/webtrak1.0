import asyncio
from types import SimpleNamespace

from app.services.bgv_service import BgvService
from app.schemas.bgv import BgvUpsertRequest


class _FakeBgvRepo:
    def __init__(self):
        self.users = {"WK1": SimpleNamespace(id=1, emp_id="WK1", name="Alice", role="SE", email="a@example.com")}
        self.rows = {}

    async def get_user_by_emp_id(self, emp_id: str):
        return self.users.get(emp_id)

    async def upsert_for_user(self, *, user_id: int, actor_id: int, payload: dict):
        _ = actor_id
        self.rows[user_id] = payload
        return SimpleNamespace(**payload)

    async def get_with_user_and_band(self, *, user_id: int):
        if user_id not in self.rows:
            return None
        user = next(v for v in self.users.values() if v.id == user_id)
        band = SimpleNamespace(name="L2")
        return SimpleNamespace(**self.rows[user_id]), user, band

    async def list_dashboard_rows(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        overall_status: str | None,
        employment_status: str | None,
        reference_status: str | None,
    ):
        _ = page, size, search, overall_status, employment_status, reference_status
        bgv = SimpleNamespace(
            consent_form_signed=True,
            identity="AADHAAR",
            employment_status="VERIFIED",
            overall_status="CLEAR",
        )
        user = self.users["WK1"]
        return [(bgv, user)], 1


class _FakeUserRepo:
    async def get_by_email(self, email: str):
        if email == "hr@example.com":
            return SimpleNamespace(id=100, email=email)
        return None


def _service():
    service = object.__new__(BgvService)
    service.bgv_repo = _FakeBgvRepo()
    service.user_repo = _FakeUserRepo()
    return service


def test_bgv_upsert_and_get_manual_status_and_independent_onboarding() -> None:
    service = _service()
    payload = BgvUpsertRequest(
        consent_form_signed=True,
        identity="Aadhaar",
        employment_status="verified",
        reference_status="completed",
        mail_id_verified="wk1@company.com",
        onboarding_form_status="filled",
        overall_status="flagged",
        remarks="manual status set by hr",
    )
    result = asyncio.run(service.upsert_record(actor_email="hr@example.com", emp_id="WK1", payload=payload))
    assert result.overall_status == "FLAGGED"
    assert result.onboarding_form_status == "FILLED"
    assert result.employment_status == "VERIFIED"


def test_bgv_dashboard_list_returns_rows() -> None:
    service = _service()
    page = asyncio.run(
        service.list_dashboard(
            page=0,
            size=10,
            search=None,
            overall_status=None,
            employment_status=None,
            reference_status=None,
        )
    )
    assert page.total_element == 1
    assert page.data[0].employee == "Alice"
