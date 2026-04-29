from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.access import get_actor_email, get_actor_roles
from app.core.database import get_db
from app.core.settings import get_settings
from app.schemas.common import GenericResponse
from app.schemas.role import AssignRoleRequest, AssignRoleRequestJava, AssignRoleResponse
from app.tools.role_tool import RoleTool

router = APIRouter()


def _resolve_actor(request: Request) -> tuple[str, set[str]]:
    try:
        return get_actor_email(request), get_actor_roles(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return "anonymous", set()
        raise


@router.post("/roles/assign", response_model=AssignRoleResponse)
async def assign_role(
    payload: AssignRoleRequest,
    request: Request,
    x_admin_bootstrap_key: str | None = Header(default=None),
    db=Depends(get_db),
) -> AssignRoleResponse:
    settings = get_settings()
    actor_email, actor_roles = _resolve_actor(request)
    tool = RoleTool(db)
    return await tool.assign_role(
        payload=payload,
        actor_email=actor_email,
        actor_roles=actor_roles,
        bootstrap_key=x_admin_bootstrap_key,
        configured_bootstrap_key=settings.admin_bootstrap_key,
    )


@router.post("/assign-role", response_model=GenericResponse)
async def assign_role_java_contract(
    payload: AssignRoleRequestJava,
    request: Request,
    x_admin_bootstrap_key: str | None = Header(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    settings = get_settings()
    actor_email, actor_roles = _resolve_actor(request)
    tool = RoleTool(db)
    result = await tool.assign_role(
        payload=AssignRoleRequest(target_email=payload.userEmail, role=payload.roleName),
        actor_email=actor_email,
        actor_roles=actor_roles,
        bootstrap_key=x_admin_bootstrap_key,
        configured_bootstrap_key=settings.admin_bootstrap_key,
    )
    return GenericResponse(message="success", data=result.model_dump())
