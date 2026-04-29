from fastapi import HTTPException, status

from app.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = RoleRepository(db)

    @staticmethod
    def _normalize_role(role: str) -> str:
        normalized = role.strip().upper()
        if not normalized.startswith("ROLE_"):
            normalized = f"ROLE_{normalized}"
        return normalized

    async def assign_role(
        self,
        actor_email: str,
        actor_roles: set[str],
        target_email: str,
        requested_role: str,
        bootstrap_key: str | None,
        configured_bootstrap_key: str,
    ) -> tuple[str, str]:
        role = self._normalize_role(requested_role)
        actor_roles = {self._normalize_role(r) for r in actor_roles}

        is_bootstrap = bool(
            configured_bootstrap_key and bootstrap_key and bootstrap_key == configured_bootstrap_key
        )
        if not is_bootstrap:
            actor = (actor_email or "").strip().lower()
            if not actor or actor == "anonymous":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
            if not actor_roles.intersection({"ROLE_ADMIN", "ROLE_HR"}):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

        if role not in {"ROLE_ADMIN", "ROLE_HR", "ROLE_FINANCE"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported role for this endpoint")

        target_user = await self.repo.get_user_by_email(target_email)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

        role_row = await self.repo.get_or_create_role(role)
        already = await self.repo.user_has_role(target_user.id, role_row.id)
        if not already:
            await self.repo.assign_role(target_user.id, role_row.id)

        return role, actor_email
