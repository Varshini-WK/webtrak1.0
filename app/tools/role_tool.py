from app.schemas.role import AssignRoleRequest, AssignRoleResponse
from app.services.role_service import RoleService


class RoleTool:
    def __init__(self, db) -> None:
        self.service = RoleService(db)

    async def assign_role(
        self,
        payload: AssignRoleRequest,
        actor_email: str,
        actor_roles: set[str],
        bootstrap_key: str | None,
        configured_bootstrap_key: str,
    ) -> AssignRoleResponse:
        assigned_role, assigned_by = await self.service.assign_role(
            actor_email=actor_email,
            actor_roles=actor_roles,
            target_email=str(payload.target_email),
            requested_role=payload.role,
            bootstrap_key=bootstrap_key,
            configured_bootstrap_key=configured_bootstrap_key,
        )
        return AssignRoleResponse(
            target_email=payload.target_email,
            assigned_role=assigned_role,
            assigned_by=assigned_by,
            message="Role assigned successfully",
        )
