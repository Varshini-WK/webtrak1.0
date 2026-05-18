import asyncio
from datetime import date
from types import SimpleNamespace

from app.services.reporting_service import ReportingService


class _FakeRepo:
    def __init__(self, users, allocations, yoe_map, skill_rows=None, cert_rows=None):
        self._users = users
        self._allocations = allocations
        self._yoe_map = yoe_map
        self._skill_rows = skill_rows or []
        self._cert_rows = cert_rows or []

    async def list_users_for_workforce_overview(self, *, search, statuses):
        _ = search, statuses
        return self._users

    async def list_active_allocation_billing_statuses(self):
        return self._allocations

    async def list_profile_yoe(self, user_ids):
        _ = user_ids
        return self._yoe_map

    async def list_active_allocations_for_users(self, *, user_ids, as_of):
        _ = user_ids, as_of
        return self._allocations

    async def list_users_for_skill_inventory(self, *, search, statuses):
        _ = search, statuses
        return self._skill_rows

    async def list_certification_documents_by_users(self, *, user_ids):
        _ = user_ids
        return self._cert_rows

    async def count_workforce_by_employment_type(self, *, statuses):
        _ = statuses
        counts: dict[str, int] = {}
        for user in self._users:
            key = str(getattr(user, "user_type", "UNKNOWN") or "UNKNOWN")
            counts[key] = counts.get(key, 0) + 1
        return [(k, v) for k, v in counts.items()]


def _service_with_repo(repo):
    service = object.__new__(ReportingService)
    service.repo = repo
    return service


def test_headcount_distribution_groups_by_department_type_and_designation() -> None:
    users = [
        SimpleNamespace(id=1, department="Engineering", role="Software Engineer", delivery_status="DELIVERABLE"),
        SimpleNamespace(id=2, department="Engineering", role="Software Engineer", delivery_status="DELIVERABLE"),
        SimpleNamespace(id=3, department="HR", role="HR Executive", delivery_status="NON_DELIVERABLE"),
    ]
    service = _service_with_repo(_FakeRepo(users, [], {}))
    result = asyncio.run(service.get_headcount_distribution(page=0, size=20, search=None))

    assert result.total_element == 2
    data = {(r.department, r.department_type, r.designation): r.total_headcount for r in result.data}
    assert data[("Engineering", "DELIVERABLE", "Software Engineer")] == 2
    assert data[("HR", "NON_DELIVERABLE", "HR Executive")] == 1


def test_role_wise_billed_mapping_uses_billed_buffer_vs_bench_investment() -> None:
    users = [
        SimpleNamespace(id=1, role="Software Engineer", delivery_status="DELIVERABLE"),
        SimpleNamespace(id=2, role="Software Engineer", delivery_status="DELIVERABLE"),
        SimpleNamespace(id=3, role="HR Executive", delivery_status="NON_DELIVERABLE"),
    ]
    # user1 billed, user2 unbilled, user3 billed.
    allocations = [
        (1, "BILLED"),
        (2, "BENCH"),
        (3, "BUFFER"),
    ]
    service = _service_with_repo(_FakeRepo(users, allocations, {}))
    result = asyncio.run(service.get_role_wise_billed(page=0, size=20, search=None))

    rows = {(r.role, r.department_type): r for r in result.data}
    se = rows[("Software Engineer", "DELIVERABLE")]
    assert se.total_count == 2
    assert se.billed_count == 1
    assert se.unbilled_count == 1
    assert se.billed_percent == 50.0
    assert se.unbilled_percent == 50.0

    hr = rows[("HR Executive", "NON_DELIVERABLE")]
    assert hr.total_count == 1
    assert hr.billed_count == 1
    assert hr.unbilled_count == 0
    assert hr.billed_percent == 100.0


def test_experience_formats_webknot_and_total_experience() -> None:
    users = [
        SimpleNamespace(
            id=10,
            emp_id="WK10",
            email="a@example.com",
            name="Alice",
            department="Engineering",
            role="Senior Engineer",
            delivery_status="DELIVERABLE",
            doj=date(2024, 4, 1),
        )
    ]
    # previous experience in years
    yoe_map = {10: 3}
    service = _service_with_repo(_FakeRepo(users, [], yoe_map))
    result = asyncio.run(service.get_experience(page=0, size=20, search=None))

    assert result.total_element == 1
    row = result.data[0]
    assert row.webknot_experience.endswith("M")
    assert row.total_experience.endswith("M")
    assert row.department_type == "DELIVERABLE"


def test_utilization_by_department_uses_fractional_allocation_shares() -> None:
    users = [
        SimpleNamespace(
            id=1,
            emp_id="WK1",
            email="u1@example.com",
            name="U1",
            department="Engineering",
            role="SE",
            delivery_status="DELIVERABLE",
        ),
        SimpleNamespace(
            id=2,
            emp_id="WK2",
            email="u2@example.com",
            name="U2",
            department="Engineering",
            role="SE",
            delivery_status="DELIVERABLE",
        ),
        SimpleNamespace(
            id=3,
            emp_id="WK3",
            email="u3@example.com",
            name="U3",
            department="Design",
            role="Designer",
            delivery_status="DELIVERABLE",
        ),
    ]
    allocations = [
        (1, 4, "BILLED", "P1", date(2026, 4, 1)),
        (1, 4, "BUFFER", "P2", date(2026, 4, 1)),
        (2, 8, "INVESTMENT", "P3", date(2026, 4, 1)),
        (3, 8, "TALENT_POOL", "BENCH", date(2026, 4, 20)),
    ]
    service = _service_with_repo(_FakeRepo(users, allocations, {}))

    result = asyncio.run(
        service.get_utilization_by_department(page=0, size=20, search=None, as_of=date(2026, 4, 30))
    )

    rows = {r.department: r for r in result.data if r.department != "Total"}
    eng = rows["Engineering"]
    assert eng.head_count == 2
    assert eng.actual_billed == 0.5
    assert eng.buffer == 0.5
    assert eng.investment == 1.0
    assert eng.talent_pool == 0.0
    assert eng.utilization_percent == 25.0

    des = rows["Design"]
    assert des.head_count == 1
    assert des.actual_billed == 0.0
    assert des.talent_pool == 1.0
    assert des.utilization_percent == 0.0

    total = next(r for r in result.data if r.department == "Total")
    assert total.head_count == 3
    assert total.actual_billed == 0.5
    assert total.buffer == 0.5
    assert total.investment == 1.0
    assert total.talent_pool == 1.0
    assert total.utilization_percent == 16.67


def test_bench_aging_only_returns_fully_bench_users() -> None:
    users = [
        SimpleNamespace(
            id=1,
            emp_id="WK1",
            email="bench@example.com",
            name="Bench User",
            department="Engineering",
            role="SE",
            delivery_status="DELIVERABLE",
        ),
        SimpleNamespace(
            id=2,
            emp_id="WK2",
            email="mixed@example.com",
            name="Mixed User",
            department="Engineering",
            role="SE",
            delivery_status="DELIVERABLE",
        ),
    ]
    allocations = [
        (1, 8, None, "BENCH", date(2026, 4, 20)),
        (2, 4, None, "BENCH", date(2026, 4, 20)),
        (2, 4, "BILLED", "P1", date(2026, 4, 20)),
    ]
    service = _service_with_repo(_FakeRepo(users, allocations, {}))

    result = asyncio.run(service.get_bench_aging(page=0, size=20, search=None, as_of=date(2026, 4, 30)))
    assert result.total_element == 1
    row = result.data[0]
    assert row.emp_id == "WK1"
    assert row.bench_days == 10


def test_skill_inventory_returns_json_skills_with_multiple_certifications() -> None:
    skill_rows = [
        (
            1,
            "WK1",
            "alice@example.com",
            "Alice",
            "Engineering",
            "Senior Engineer",
            ["Python", "FastAPI"],
            [{"skill": "React", "rating": 4}, {"skill": "Kubernetes", "rating": 3}],
        ),
        (
            2,
            "WK2",
            "bob@example.com",
            "Bob",
            "QA",
            "QA Engineer",
            None,
            [{"skill": "Playwright", "rating": 5}, {"skill": "", "rating": 1}, {"rating": 3}],
        ),
    ]
    cert_rows = [
        (1, "https://files/cert-a.pdf"),
        (1, "https://files/cert-b.pdf"),
    ]
    service = _service_with_repo(_FakeRepo([], [], {}, skill_rows=skill_rows, cert_rows=cert_rows))

    result = asyncio.run(service.get_skill_inventory(page=0, size=20, search=None))
    assert result.total_element == 2

    alice = next(row for row in result.data if row.emp_id == "WK1")
    assert alice.primary_skills == ["Python", "FastAPI"]
    assert [item.model_dump() for item in alice.secondary_skills] == [
        {"skill": "React", "rating": 4},
        {"skill": "Kubernetes", "rating": 3},
    ]
    assert alice.certifications == ["https://files/cert-a.pdf", "https://files/cert-b.pdf"]

    bob = next(row for row in result.data if row.emp_id == "WK2")
    assert bob.primary_skills == []
    assert [item.model_dump() for item in bob.secondary_skills] == [{"skill": "Playwright", "rating": 5}]
    assert bob.certifications == []


def test_contract_distribution_counts_and_percentage() -> None:
    users = [
        SimpleNamespace(id=1, user_type="FULLTIME"),
        SimpleNamespace(id=2, user_type="FULLTIME"),
        SimpleNamespace(id=3, user_type="INTERN"),
        SimpleNamespace(id=4, user_type="CONSULTANT"),
    ]
    service = _service_with_repo(_FakeRepo(users, [], {}))
    result = asyncio.run(service.get_contract_distribution(page=0, size=20))

    rows = {row.employment_type: row for row in result.data}
    assert rows["Full-Time"].count == 2
    assert rows["Intern"].count == 1
    assert rows["Consultant"].count == 1
    assert rows["Total"].count == 4
    assert rows["Total"].workforce_percent == 100.0

