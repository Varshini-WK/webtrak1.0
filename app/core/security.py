from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.core.settings import get_settings


def create_access_token(subject: str, roles: list[str], status: str, user_type: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "roles": roles,
        "status": status,
        "type": user_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.InvalidTokenError:
        return None

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        return None

    roles = payload.get("roles")
    if not isinstance(roles, list):
        roles = []
    roles = [str(role) for role in roles if str(role).strip()]

    status = payload.get("status")
    user_type = payload.get("type")
    return {
        "sub": sub.strip(),
        "roles": roles,
        "status": str(status) if status is not None else "",
        "type": str(user_type) if user_type is not None else "",
    }


def create_refresh_token() -> tuple[str, str, datetime]:
    settings = get_settings()
    token_id = str(uuid4())
    token = str(uuid4())
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_days)
    return token_id, token, expires_at
