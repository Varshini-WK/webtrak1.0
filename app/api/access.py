from fastapi import HTTPException, Request, status

from app.core.security import decode_access_token
from app.core.settings import get_settings


def _normalize_role_token(role: str) -> str:
    r = role.strip().upper()
    if not r.startswith("ROLE_"):
        r = f"ROLE_{r}"
    return r


def _extract_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "").strip()
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0], parts[1].strip()
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _decode_bearer_claims(request: Request) -> dict | None:
    token = _extract_bearer_token(request)
    if not token:
        return None
    return decode_access_token(token)


def get_actor_email(request: Request) -> str:
    email = request.cookies.get("email")
    if email:
        return email

    claims = _decode_bearer_claims(request)
    bearer_sub = claims.get("sub") if claims else None
    if isinstance(bearer_sub, str) and bearer_sub.strip():
        return bearer_sub.strip()

    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_actor_roles(request: Request) -> set[str]:
    raw_roles = request.cookies.get("roles", "")
    if raw_roles.strip():
        return {_normalize_role_token(role) for role in raw_roles.split(",") if role.strip()}

    bearer_token = _extract_bearer_token(request)
    claims = _decode_bearer_claims(request)
    if bearer_token and claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")
    roles = claims.get("roles") if claims else []
    return {_normalize_role_token(str(role)) for role in roles if str(role).strip()}


def require_any_role(request: Request, allowed_roles: set[str]) -> None:
    settings = get_settings()
    if not settings.enable_role_checks:
        return
    roles = get_actor_roles(request)
    if not roles.intersection(allowed_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def has_all_roles(roles: set[str], required_roles: set[str]) -> bool:
    """True when every required role is present (e.g. both HR and Admin)."""
    required = {_normalize_role_token(r) for r in required_roles}
    return required.issubset(roles)


def require_all_roles(request: Request, required_roles: set[str]) -> None:
    settings = get_settings()
    if not settings.enable_role_checks:
        return
    roles = get_actor_roles(request)
    if not has_all_roles(roles, required_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
