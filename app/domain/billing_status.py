from app.domain.work_profile import normalize_choice

BILLING_STATUS_VALUES = frozenset({"BILLED", "BUFFER", "INVESTMENT"})


def normalize_billing_status(value: str | None) -> str | None:
    return normalize_choice(value, BILLING_STATUS_VALUES, "billing_status")
