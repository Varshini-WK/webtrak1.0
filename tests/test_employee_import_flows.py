import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from types import SimpleNamespace

from openpyxl import Workbook

from app.services.employee_service import EmployeeService


@dataclass
class FakeUser:
    id: int
    email: str
    name: str
    status: str = "INVITED"
    user_type: str = "FULLTIME"
    department: str | None = None
    phone_number: str | None = None
    role: str | None = None
    work_mode: str | None = None
    work_location_type: str | None = None
    doj: date | None = None
    doi: date | None = None
    internship_duration: int | None = None
    band_id: int | None = None
    emp_id: str | None = None


class FakeDB:
    @asynccontextmanager
    async def tx(self):
        yield self


class FakeEmployeeRepo:
    def __init__(self):
        self.users: dict[str, FakeUser] = {}
        self.next_id = 1
        self.created_payloads: list[dict] = []
        self.updated_payloads: list[dict] = []
        self.role_assignments: list[tuple[int, int, str | None]] = []
        self.bench_allocations: list[dict] = []

    async def get_user_by_email(self, email: str):
        return self.users.get(email.lower())

    async def create_user(self, data: dict, client=None):
        _ = client
        user = FakeUser(
            id=self.next_id,
            emp_id=data.get("empId"),
            email=str(data["email"]).lower(),
            name=data["name"],
            status=data.get("status", "INVITED"),
            user_type=data.get("userType", "FULLTIME"),
            department=data.get("department"),
            phone_number=data.get("phoneNumber"),
            role=data.get("role"),
            work_mode=data.get("workMode"),
            work_location_type=data.get("workLocationType"),
            doj=data.get("doj"),
            doi=data.get("doi"),
            internship_duration=data.get("internshipDuration"),
            band_id=data.get("bandId"),
        )
        self.next_id += 1
        self.users[user.email] = user
        self.created_payloads.append(dict(data))
        return user

    async def update_user(self, user_id: int, data: dict, client=None):
        _ = client
        user = next(u for u in self.users.values() if u.id == user_id)
        mapping = {
            "empId": "emp_id",
            "email": "email",
            "name": "name",
            "status": "status",
            "userType": "user_type",
            "department": "department",
            "phoneNumber": "phone_number",
            "role": "role",
            "workMode": "work_mode",
            "workLocationType": "work_location_type",
            "doj": "doj",
            "doi": "doi",
            "internshipDuration": "internship_duration",
            "bandId": "band_id",
        }
        old_email = user.email
        for key, value in data.items():
            setattr(user, mapping[key], value)
        if user.email != old_email:
            self.users.pop(old_email, None)
            self.users[user.email] = user
        self.updated_payloads.append(dict(data))
        return user

    async def get_or_create_role(self, role_name: str):
        return SimpleNamespace(id=1, name=role_name)

    async def assign_role(self, user_id: int, role_id: int, project_code: str | None = "GLOBAL", client=None):
        _ = client
        self.role_assignments.append((user_id, role_id, project_code))
        return SimpleNamespace(user_id=user_id, role_id=role_id, project_code=project_code)

    async def create_bench_allocation(self, user_id: int, role: str | None, start_date, client=None):
        _ = client
        self.bench_allocations.append({"user_id": user_id, "role": role, "start_date": start_date})
        return SimpleNamespace(id=len(self.bench_allocations), user_id=user_id)


class FakeLeaveRepo:
    def __init__(self):
        self.mappings: list[dict] = []

    async def create_mapping(self, user_id: int, year: int, month: int, primary_leave: float, secondary_leave: float, carry_forward: float = 0.0, client=None):
        _ = client
        self.mappings.append(
            {
                "user_id": user_id,
                "year": year,
                "month": month,
                "primary_leave": primary_leave,
                "secondary_leave": secondary_leave,
                "carry_forward": carry_forward,
            }
        )
        return SimpleNamespace(id=len(self.mappings), user_id=user_id)


def _excel_bytes(rows: list[list]):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_service(repo: FakeEmployeeRepo) -> EmployeeService:
    service = EmployeeService(FakeDB())
    service.employee_repo = repo
    service.leave_repo = FakeLeaveRepo()
    return service


def test_bulk_upload_users_accepts_full_user_headers():
    repo = FakeEmployeeRepo()
    service = _make_service(repo)
    content = _excel_bytes(
        [
            ["emp_id", "email", "name", "status", "user_type", "department", "phone_number", "role", "work_mode", "work_location_type", "doj", "doi", "internship_duration", "band_id"],
            ["WK001", "new.user@example.com", "New User", "ACTIVE", "FULLTIME", "Engineering", "9876543210", "Developer", "HYBRID", "ONSITE", "2026-04-01", "", 6, 4],
        ]
    )
    result = asyncio.run(service.bulk_upload_users(content))
    assert result["processed"] == 1
    assert result["skipped"] == 0
    created = repo.users["new.user@example.com"]
    assert created.emp_id == "WK001"
    assert created.role == "Developer"
    assert created.work_mode == "HYBRID"
    assert created.work_location_type == "ONSITE"
    assert created.band_id == 4
    assert len(repo.role_assignments) == 1
    assert len(repo.bench_allocations) == 1
    assert len(service.leave_repo.mappings) == 1
    assert service.leave_repo.mappings[0]["primary_leave"] == 1.5
    assert service.leave_repo.mappings[0]["secondary_leave"] == 0.0


def test_bulk_upload_users_legacy_three_column_fallback():
    repo = FakeEmployeeRepo()
    service = _make_service(repo)
    # No header row; legacy positional fallback should apply.
    content = _excel_bytes(
        [
            ["WK010", "Legacy User", "legacy.user@example.com"],
        ]
    )
    result = asyncio.run(service.bulk_upload_users(content))
    assert result["processed"] == 1
    assert repo.users["legacy.user@example.com"].name == "Legacy User"
    assert repo.users["legacy.user@example.com"].emp_id == "WK010"
    assert len(repo.bench_allocations) == 1
    assert len(service.leave_repo.mappings) == 1


def test_import_user_data_updates_existing_users_with_full_headers_and_skips_unknown():
    repo = FakeEmployeeRepo()
    existing = FakeUser(id=1, email="known.user@example.com", name="Known User")
    repo.users[existing.email] = existing
    service = _make_service(repo)
    content = _excel_bytes(
        [
            ["email", "name", "status", "user_type", "department", "phone_number", "role", "work_mode", "work_location_type", "doj", "doi", "internship_duration", "band_id"],
            ["known.user@example.com", "Known User", "ACTIVE", "FULLTIME", "QA", "9000000000", "QA Lead", "ONSITE", "REMOTE", "2026-03-10", "2026-03-01", "x", "invalid"],
            ["missing.user@example.com", "Missing User", "ACTIVE", "FULLTIME", "Engineering", "9000000001", "Dev", "HYBRID", "2026-03-11", "", 3, 2],
        ]
    )
    result = asyncio.run(service.import_user_data(content))
    assert result["processed"] == 1
    assert result["skipped"] == 1
    assert existing.status == "ACTIVE"
    assert existing.user_type == "FULLTIME"
    assert existing.department == "QA"
    assert existing.phone_number == "9000000000"
    assert existing.role == "QA Lead"
    assert existing.work_mode == "ONSITE"
    assert existing.work_location_type == "REMOTE"
    assert existing.doj == date(2026, 3, 10)
    assert existing.doi == date(2026, 3, 1)
    # Invalid numeric values are ignored rather than crashing.
    assert existing.internship_duration is None
    assert existing.band_id is None


def test_import_user_data_legacy_positional_fallback():
    repo = FakeEmployeeRepo()
    existing = FakeUser(id=5, email="legacy.update@example.com", name="Legacy Update")
    repo.users[existing.email] = existing
    service = _make_service(repo)
    # No header row; legacy /upload/user-data positional mapping.
    content = _excel_bytes(
        [
            ["unused", "legacy.update@example.com", "FULLTIME", "ACTIVE", 8, "2026-01-10", "9999999999", "Administration"],
        ]
    )
    result = asyncio.run(service.import_user_data(content))
    assert result["processed"] == 1
    assert existing.user_type == "FULLTIME"
    assert existing.status == "ACTIVE"
    assert existing.band_id == 8
    assert existing.phone_number == "9999999999"
    assert existing.department == "Administration"
