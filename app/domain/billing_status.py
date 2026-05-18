from app.domain.work_profile import normalize_choice

BILLING_STATUS_VALUES = frozenset({"BILLED", "BUFFER", "INVESTMENT", "TALENT_POOL"})
TALENT_POOL_BILLING_STATUS = "TALENT_POOL"


def normalize_billing_token(value: str | None) -> str:
    return (value or "").strip().upper().replace("-", "_").replace(" ", "_")


def is_talent_pool_billing(value: str | None) -> bool:
    return normalize_billing_token(value) == TALENT_POOL_BILLING_STATUS


def normalize_billing_status(value: str | None) -> str | None:
    return normalize_choice(value, BILLING_STATUS_VALUES, "billing_status")
