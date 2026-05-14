"""Auto-generated client project codes: P001_CLIENTSLUG style."""

from __future__ import annotations

import re

_CODE_MAX_LEN = 100


def slug_from_label(label: str, max_len: int = 40) -> str:
    raw = (label or "").strip().upper()
    raw = re.sub(r"[^A-Z0-9]+", "_", raw)
    raw = raw.strip("_")[:max_len].strip("_")
    return raw or "CLIENT"


def format_auto_project_code(sequence: int, client_name: str) -> str:
    token = slug_from_label(client_name)
    base = f"P{sequence:03d}_{token}"
    return base[:_CODE_MAX_LEN]
