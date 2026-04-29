import asyncio
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.user_request import UserRequestCreate, UserRequestStatusUpdate
from app.services.scheduled_jobs_service import ScheduledJobsService
from app.services.user_request_service import UserRequestService


class _AsyncCtx:
    def __init__(self, obj):
        self.obj = obj

    async def __aenter__(self):
        return self.obj

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeTx:
    def __init__(self):
        self.deleted: list = []

    async def scalar(self, _stmt):
        return self.mapping

    async def scalars(self, _stmt):
        return []

    async def execute(self, _stmt):
        class _Rows:
            def all(self):
                return []

            def first(self):
                return None

        return _Rows()

    def add(self, _obj):
        return None

    async def flush(self):
        return None

    async def delete(self, obj):
        self.deleted.append(obj)


def test_user_request_schema_accepts_client_approval_alias():
    payload = UserRequestCreate.model_validate(
        {
            "requestFromDate": "2026-04-13",
            "requestToDate": "2026-04-13",
            "userRequestType": "LEAVE",
            "clientApproval": True,
        }
    )
    assert payload.client_approval is True


def test_working_days_skips_weekends_and_holidays():
    service = object.__new__(UserRequestService)
    service._is_non_optional_holiday = lambda d: d == date(2026, 4, 14)  # type: ignore[method-assign]
    days = service._working_days(date(2026, 4, 10), date(2026, 4, 14))
    assert days == [date(2026, 4, 10), date(2026, 4, 13)]


def test_deduction_primary_first_and_split_markers():
    service = object.__new__(UserRequestService)
    service._can_apply_leave = lambda _user, _day: True  # type: ignore[method-assign]
    fake_leave_tx_repo = SimpleNamespace(rows=[])

    async def _create_many(rows, client=None):
        _ = client
        fake_leave_tx_repo.rows = rows
        return rows

    fake_leave_tx_repo.create_many = _create_many
    service.leave_tx_repo = fake_leave_tx_repo

    tx = _FakeTx()
    tx.mapping = SimpleNamespace(primary_leave=1.0, secondary_leave=1.0)

    asyncio.run(
        service._deduct_leave_for_date_range(
            user_id=1,
            user=SimpleNamespace(id=1),
            user_request_id=77,
            from_date=date(2026, 4, 13),
            to_date=date(2026, 4, 14),
            is_half_day=False,
            approver_id=11,
            client=tx,
        )
    )

    assert tx.mapping.primary_leave == 0.0
    assert tx.mapping.secondary_leave == 0.0
    assert fake_leave_tx_repo.rows[0]["comments"] == "[D:1.0P,0.0S]"
    assert fake_leave_tx_repo.rows[1]["comments"] == "[D:0.0P,1.0S]"


def test_revert_uses_split_markers_and_deletes_transactions():
    service = object.__new__(UserRequestService)
    txn = SimpleNamespace(transaction_type="DEDUCT", value=1.0, comments="[D:1.0P,0.0S]", for_date=date(2026, 4, 13))

    async def _list_by_user_request(_user_request_id, client=None):
        _ = client
        return [txn]

    service.leave_tx_repo = SimpleNamespace(list_by_user_request=_list_by_user_request)
    tx = _FakeTx()
    tx.mapping = SimpleNamespace(primary_leave=0.5, secondary_leave=-0.5)

    asyncio.run(service._revert_leave_for_request(user_id=1, user_request_id=77, client=tx))

    assert tx.mapping.primary_leave == 1.0
    assert tx.mapping.secondary_leave == 0.0
    assert tx.deleted == [txn]


def test_update_status_blocks_duplicate_same_action():
    service = object.__new__(UserRequestService)
    service._get_user_by_email_or_404 = lambda _email: _async_return(SimpleNamespace(id=12, email="hr@example.com"))  # type: ignore[method-assign]
    service._is_hr_user = lambda _uid, _client: _async_return(True)  # type: ignore[method-assign]
    service.request_repo = SimpleNamespace(
        get_by_id_with_lock=lambda _id, _tx: _async_return(
            SimpleNamespace(
                id=99,
                user_id=22,
                user=SimpleNamespace(id=22, email="u@example.com"),
                request_type="LEAVE",
                request_from_date=date(2026, 4, 13),
                request_to_date=date(2026, 4, 13),
                is_half_day=False,
                status="PENDING",
            )
        )
    )
    service.tracking_repo = SimpleNamespace(
        list_by_request_and_actioner=lambda _rid, _aid: _async_return([SimpleNamespace(action="APPROVED")])
    )
    service.db = SimpleNamespace(tx=lambda: _AsyncCtx(_FakeTx()))

    with pytest.raises(HTTPException) as err:
        asyncio.run(
            service.update_status(
                actor_email="hr@example.com",
                actor_roles={"ROLE_HR"},
                payload=UserRequestStatusUpdate(user_request_id=99, user_request_status="APPROVED", message=None),
            )
        )
    assert err.value.status_code == 400
    assert "already Approved" in err.value.detail


def test_scheduler_auto_approve_is_tracking_only():
    service = object.__new__(ScheduledJobsService)
    request = SimpleNamespace(id=44, user_id=7, status="PENDING")
    service.request_repo = SimpleNamespace(list_pending_for_exact_day=lambda day, request_types: _async_return([request]))
    service.tracking_repo = SimpleNamespace(
        has_action_for_request_and_actioners=lambda **_kwargs: _async_return(False),
        create=lambda payload, client=None: _async_return(payload),
    )
    service.notification_service = SimpleNamespace(send_notification=lambda **_kwargs: _async_return(None))
    service._manager_actioner_ids = lambda _request_id, _tx: _async_return([501])  # type: ignore[method-assign]
    service.db = SimpleNamespace(tx=lambda: _AsyncCtx(_FakeTx()))

    created = asyncio.run(service.auto_approve_leave_if_manager_not_approved())

    assert created == 1
    assert request.status == "PENDING"


def _async_return(value):
    async def _inner(*_args, **_kwargs):
        return value

    return _inner()
