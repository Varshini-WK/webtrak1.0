from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.learning import TrainingCreateRequest, TrainingUpdateRequest


def test_training_create_rejects_end_before_start() -> None:
    with pytest.raises(ValidationError):
        TrainingCreateRequest(
            name="X",
            category="TECHNICAL",
            type="OPTIONAL",
            start_date=date(2026, 6, 10),
            end_date=date(2026, 6, 1),
        )


def test_training_create_accepts_same_day() -> None:
    d = date(2026, 6, 1)
    t = TrainingCreateRequest(name="X", category="TECHNICAL", type="OPTIONAL", start_date=d, end_date=d)
    assert t.start_date == t.end_date


def test_training_update_partial_dates_validated_when_both_present() -> None:
    with pytest.raises(ValidationError):
        TrainingUpdateRequest(start_date=date(2026, 6, 20), end_date=date(2026, 6, 1))
