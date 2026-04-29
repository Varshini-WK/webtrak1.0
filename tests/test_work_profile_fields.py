from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.allocation_rules import AllocationType
from app.schemas.allocation import AllocationCreateRequest
from app.schemas.employee import UserOnboardCreate


def test_onboard_create_accepts_delivery_and_work_location_type():
    payload = UserOnboardCreate(
        email="member@example.com",
        name="Member",
        user_type="FULLTIME",
        department="Engineering",
        phone_number="9999999999",
        work_mode="HYBRID",
        work_location_type="remote",
        role="Software Engineer",
        band_id=2,
        doj=date(2026, 4, 1),
    )
    assert payload.work_location_type == "REMOTE"


def test_onboard_create_rejects_invalid_work_location_type():
    with pytest.raises(ValidationError):
        UserOnboardCreate(
            email="member@example.com",
            name="Member",
            user_type="FULLTIME",
            department="Engineering",
            phone_number="9999999999",
            work_mode="HYBRID",
            work_location_type="TRAVEL",
            role="Software Engineer",
            band_id=2,
            doj=date(2026, 4, 1),
        )


def test_onboard_create_requires_intern_fields_for_intern():
    with pytest.raises(ValidationError):
        UserOnboardCreate(
            email="intern@example.com",
            name="Intern",
            user_type="INTERN",
            department="Engineering",
            phone_number="9999999999",
            work_mode="ONSITE",
            work_location_type="ONSITE",
            role="Golang Intern",
            band_id=1,
        )


def test_onboard_create_requires_doj_for_fulltime_and_consultant():
    with pytest.raises(ValidationError):
        UserOnboardCreate(
            email="consultant@example.com",
            name="Consultant",
            user_type="CONSULTANT",
            department="Delivery",
            phone_number="8888888888",
            work_mode="REMOTE",
            work_location_type="REMOTE",
            role="Senior QA",
            band_id=3,
        )


def test_onboard_update_accepts_secondary_skills_with_rating():
    from app.schemas.employee import UserOnboardUpdate

    payload = UserOnboardUpdate(
        email="member@example.com",
        primary_skills=["Python"],
        secondary_skills=[{"skill": "React", "rating": 4}, {"skill": "Docker", "rating": 3}],
    )
    assert payload.secondary_skills[0].skill == "React"


def test_onboard_update_rejects_secondary_skill_without_rating():
    from app.schemas.employee import UserOnboardUpdate

    with pytest.raises(ValidationError):
        UserOnboardUpdate(
            email="member@example.com",
            primary_skills=["Python"],
            secondary_skills=[{"skill": "React"}],
        )


def test_allocation_create_accepts_work_location_type_alias():
    payload = AllocationCreateRequest(
        employeeEmail="member@example.com",
        projectCode="ABC",
        allocatedHours=8,
        startDate=date(2026, 4, 27),
        allocationType=AllocationType.DEPLOYABLE,
        workLocationType="onsite",
    )
    assert payload.work_location_type == "ONSITE"


def test_allocation_create_rejects_invalid_work_location_type():
    with pytest.raises(ValidationError):
        AllocationCreateRequest(
            employee_email="member@example.com",
            project_code="ABC",
            allocated_hours=8,
            start_date=date(2026, 4, 27),
            allocation_type=AllocationType.DEPLOYABLE,
            work_location_type="travel",
        )
