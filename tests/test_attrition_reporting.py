import asyncio
from datetime import date
from types import SimpleNamespace

from app.services.reporting_service import ReportingService


class _FakeAttritionRepo:
    def __init__(self, rows, *, office_headcount: int) -> None:
        self._rows = rows
        self._office_headcount = office_headcount

    async def list_with_users_for_date_range(self, *, start_inclusive: date, end_inclusive: date):
        _ = start_inclusive, end_inclusive
        return self._rows

    async def count_users_with_statuses(self, *, statuses: list[str]):
        _ = statuses
        return self._office_headcount

    async def resolve_project_manager_label(self, *, user_id: int, last_working_day: date):
        _ = user_id, last_working_day
        return None


class _FakeUserRepo:
    def __init__(self, names: dict[int, str]) -> None:
        self._names = names

    async def map_names_by_user_ids(self, user_ids: list[int]) -> dict[int, str]:
        return {i: self._names[i] for i in user_ids if i in self._names}


def _service_with_attrition_repo(fake: _FakeAttritionRepo, *, user_names: dict[int, str] | None = None) -> ReportingService:
    svc = object.__new__(ReportingService)
    svc.repo = None  # type: ignore[assignment]
    svc.attrition_repo = fake  # type: ignore[assignment]
    svc.user_repo = _FakeUserRepo(user_names or {})  # type: ignore[assignment]
    svc._ACTIVE_STATUSES = ReportingService._ACTIVE_STATUSES
    svc._SEPARATION_VOLUNTARY = ReportingService._SEPARATION_VOLUNTARY
    svc._SEPARATION_INVOLUNTARY = ReportingService._SEPARATION_INVOLUNTARY
    return svc


def test_attrition_fy_summary_percent_and_splits() -> None:
    user = SimpleNamespace(id=1, role="Software Engineer", doj=date(2024, 1, 15))
    attr = SimpleNamespace(
        separation_type="VOLUNTARY",
        designation="Software Engineer",
        project_manager="42",
        critical_skill="Python",
        is_regretted=True,
        last_working_day=date(2025, 6, 1),
    )
    fake = _FakeAttritionRepo([(attr, user)], office_headcount=95)
    svc = _service_with_attrition_repo(fake, user_names={42: "Alex Lead"})
    out = asyncio.run(svc.build_attrition_fy_report(fy_start_year=2025))

    assert out.fy_period.fy_start_year == 2025
    assert out.overall_attrition_percent.fy_start_year == 2025
    assert out.overall_attrition_percent.fy_april_start == date(2025, 4, 1)
    assert out.overall_attrition_percent.fy_march_end == date(2026, 3, 31)
    assert out.overall_attrition_percent.number_of_exits == 1
    assert out.overall_attrition_percent.attrition_percent == round(100 / 95, 2)

    assert out.voluntary_vs_involuntary.voluntary_count == 1
    assert out.voluntary_vs_involuntary.involuntary_count == 0
    assert out.voluntary_vs_involuntary.total_count == 1
    assert (
        out.voluntary_vs_involuntary.total_count
        == out.voluntary_vs_involuntary.voluntary_count + out.voluntary_vs_involuntary.involuntary_count
    )

    overall_only = asyncio.run(svc.get_attrition_overall_percent(fy_start_year=2025))
    assert overall_only.model_dump() == out.overall_attrition_percent.model_dump()

    assert asyncio.run(svc.get_attrition_voluntary_involuntary(fy_start_year=2025)).model_dump() == out.voluntary_vs_involuntary.model_dump()
    assert asyncio.run(svc.get_attrition_role_wise(fy_start_year=2025)).model_dump() == out.role_wise_attrition.model_dump()
    assert asyncio.run(svc.get_attrition_manager_wise(fy_start_year=2025)).model_dump() == out.manager_wise_attrition.model_dump()
    assert asyncio.run(svc.get_attrition_critical_skill(fy_start_year=2025)).model_dump() == out.critical_skill_attrition.model_dump()
    assert asyncio.run(svc.get_attrition_regretted(fy_start_year=2025)).model_dump() == out.regretted_attrition.model_dump()
    assert asyncio.run(svc.get_attrition_average_tenure(fy_start_year=2025)).model_dump() == out.average_tenure.model_dump()

    assert out.regretted_attrition.total_regretted_exits == 1
    assert out.regretted_attrition.percent_of_total_attrition == 100.0

    assert out.role_wise_attrition.rows[0].role_or_designation == "Software Engineer"
    assert out.manager_wise_attrition.rows[0].reporting_manager == "Alex Lead"
    assert out.critical_skill_attrition.rows[0].critical_skill == "Python"

    long_bucket = next(b for b in out.average_tenure.buckets if b.tenure_bucket == "Long Tenure")
    assert long_bucket.number_of_employees == 1
    assert out.average_tenure.average_tenure_days is not None
    assert out.average_tenure.tenure_unknown_employees == 0


def test_attrition_fy_summary_tenure_unknown_doj() -> None:
    user = SimpleNamespace(id=2, role="SE", doj=None)
    attr = SimpleNamespace(
        separation_type="INVOLUNTARY",
        designation=None,
        project_manager=None,
        critical_skill=None,
        is_regretted=False,
        last_working_day=date(2025, 12, 1),
    )
    fake = _FakeAttritionRepo([(attr, user)], office_headcount=10)
    svc = _service_with_attrition_repo(fake)
    out = asyncio.run(svc.build_attrition_fy_report(fy_start_year=2025))
    unknown = next(b for b in out.average_tenure.buckets if b.tenure_bucket == "Unknown")
    assert unknown.number_of_employees == 1
    assert out.average_tenure.average_tenure_days is None
    assert out.average_tenure.tenure_unknown_employees == 1
