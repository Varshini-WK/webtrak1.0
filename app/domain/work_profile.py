from __future__ import annotations

from collections.abc import Iterable

DELIVERY_STATUS_VALUES = frozenset({"DELIVERABLE", "NON_DELIVERABLE"})
WORK_LOCATION_TYPE_VALUES = frozenset({"OFFSHORE", "ONSITE", "HYBRID", "REMOTE"})


def normalize_choice(value: str | None, allowed: Iterable[str], field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().upper()
    if not cleaned:
        return None
    allowed_set = set(allowed)
    if cleaned not in allowed_set:
        raise ValueError(f"Invalid {field_name}: {value}")
    return cleaned
