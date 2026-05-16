from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.attrition import AttritionUpsertRequest


def test_notice_period_inclusive_days() -> None:
    payload = AttritionUpsertRequest(
        resignation_date=date(2026, 5, 1),
        last_working_day=date(2026, 5, 30),
        separation_type="VOLUNTARY",
    )
    assert payload.notice_period_days == 30


def test_notice_period_same_day() -> None:
    d = date(2026, 5, 15)
    payload = AttritionUpsertRequest(
        resignation_date=d,
        last_working_day=d,
        separation_type="INVOLUNTARY",
    )
    assert payload.notice_period_days == 1


def test_resignation_after_last_day_rejected() -> None:
    with pytest.raises(ValidationError):
        AttritionUpsertRequest(
            resignation_date=date(2026, 6, 1),
            last_working_day=date(2026, 5, 1),
            separation_type="VOLUNTARY",
        )
