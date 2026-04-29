import asyncio
from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.schemas.allocation_extension import CreateAllocationExtensionRequest, UpdateAllocationExtensionStatusRequest
from app.schemas.user_request import UserRequestCreate, UserRequestStatusUpdate
from app.services.comp_off_service import CompOffService
from app.services.user_request_service import UserRequestService


def test_user_request_schema_accepts_java_aliases():
    payload = UserRequestCreate.model_validate(
        {
            "requestFromDate": "2026-04-10",
            "requestToDate": "2026-04-10",
            "userRequestType": "LEAVE",
            "isHalfDay": True,
            "referenceFileUrl": "https://example.com/file",
        }
    )
    assert payload.request_type == "LEAVE"
    assert payload.is_half_day is True


def test_user_request_status_schema_aliases():
    payload = UserRequestStatusUpdate.model_validate(
        {
            "userRequestId": 11,
            "userRequestStatus": "APPROVED",
        }
    )
    assert payload.user_request_id == 11
    assert payload.user_request_status == "APPROVED"


def test_allocation_extension_schema_aliases():
    create_payload = CreateAllocationExtensionRequest.model_validate(
        {
            "userEmail": "person@example.com",
            "projectCode": "P001",
            "requestedEndDate": "2026-07-31",
        }
    )
    assert create_payload.project_code == "P001"
    status_payload = UpdateAllocationExtensionStatusRequest.model_validate({"requestId": 3, "status": "APPROVED"})
    assert status_payload.request_id == 3


def test_working_days_skips_weekends():
    service = object.__new__(UserRequestService)
    days = service._working_days(date(2026, 4, 10), date(2026, 4, 13))
    assert days == [date(2026, 4, 10), date(2026, 4, 13)]


def test_comp_off_consume_raises_when_balance_insufficient():
    class FakeRepo:
        async def list_active_grants(self, user_id: int, as_of: date):
            _ = (user_id, as_of)
            return []

        async def create_usage(self, payload: dict, client=None):
            _ = (payload, client)
            return None

    service = object.__new__(CompOffService)
    service.repo = FakeRepo()
    with pytest.raises(HTTPException):
        asyncio.run(
            service.consume_for_leave(
                user_request_id=7,
                user_id=9,
                for_date=date.today(),
                units=1.0,
                client=None,
            )
        )


def test_comp_off_grant_uses_90_day_validity():
    class FakeRepo:
        def __init__(self):
            self.payload = None

        async def create_grant(self, payload: dict, client=None):
            _ = client
            self.payload = payload
            return payload

    service = object.__new__(CompOffService)
    fake_repo = FakeRepo()
    service.repo = fake_repo
    asyncio.run(
        service.grant_for_approved_request(
            user_id=1,
            user_request_id=2,
            approved_by_id=3,
            request_date=date(2026, 4, 10),
            is_half_day=False,
            client=None,
        )
    )
    assert fake_repo.payload is not None
    assert fake_repo.payload["expiry_date"] == date(2026, 4, 10) + timedelta(days=90)
