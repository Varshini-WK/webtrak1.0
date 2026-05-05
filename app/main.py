from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from sqlalchemy import and_, select

from app.api.allocation import router as allocation_router
from app.api.allocation_extension import router as allocation_extension_router
from app.api.auth import router as auth_router
from app.api.bgv import router as bgv_router
from app.api.employee import router as employee_router
from app.api.learning import router as learning_router
from app.api.leave_reporting import router as leave_reporting_router
from app.api.notification import router as notification_router
from app.api.project import router as project_router
from app.api.policy import router as policy_router
from app.api.attrition_reporting import router as attrition_reporting_router
from app.api.reporting import router as reporting_router
from app.api.role import router as role_router
from app.api.scheduler import router as scheduler_router
from app.api.timelog import router as timelog_router
from app.api.reference import router as reference_router
from app.api.user_request import router as user_request_router
from app.core.database import Base, db
from app.db_insert import seed_master_data
from app.core.settings import get_settings
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.models import Project, Role, UserRole


app = FastAPI(title="Webtrak Backend", version="0.1.0")
app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
app.include_router(employee_router, prefix="/api/v1", tags=["employee"])
app.include_router(learning_router, prefix="/api/v1", tags=["learning"])
app.include_router(leave_reporting_router, prefix="/api/v1", tags=["leave-reporting"])
app.include_router(notification_router, prefix="/api/v1", tags=["notification"])
app.include_router(project_router, prefix="/api/v1", tags=["project"])
app.include_router(allocation_router, prefix="/api/v1", tags=["allocation"])
app.include_router(timelog_router, prefix="/api/v1", tags=["timelog"])
app.include_router(role_router, prefix="/api/v1", tags=["roles"])
app.include_router(user_request_router, prefix="/api/v1", tags=["user-request"])
app.include_router(allocation_extension_router, prefix="/api/v1", tags=["allocation-extension"])
app.include_router(reference_router, prefix="/api/v1", tags=["reference"])
app.include_router(scheduler_router, prefix="/api/v1", tags=["scheduler"])
app.include_router(reporting_router, prefix="/api/v1", tags=["reporting"])
app.include_router(attrition_reporting_router, prefix="/api/v1", tags=["attrition-reporting"])
app.include_router(policy_router, prefix="/api/v1", tags=["policy"])
app.include_router(bgv_router, prefix="/api/v1", tags=["bgv"])


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    request_body_schema = (
        schema.get("paths", {})
        .get("/api/v1/user/onboard", {})
        .get("put", {})
        .get("requestBody", {})
        .get("content", {})
        .get("multipart/form-data", {})
        .get("schema", {})
    )
    target = request_body_schema.get("$ref", "")
    resolved = (
        schema.get("components", {})
        .get("schemas", {})
        .get(target.split("/")[-1], {})
        if target.startswith("#/components/schemas/")
        else request_body_schema
    )
    salary_slips_schema = resolved.get("properties", {}).get("salary_slips")

    # Normalize multipart array file schema for Swagger UI file-picker rendering.
    if isinstance(salary_slips_schema, dict):
        normalized_salary_slips = {
            "title": salary_slips_schema.get("title", "Salary Slips"),
            "type": "array",
            "items": {"type": "string", "format": "binary"},
        }
        resolved.setdefault("properties", {})["salary_slips"] = normalized_salary_slips

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi

async def _seed_roles() -> None:
    expected_roles = {"ROLE_EMPLOYEE", "ROLE_HR", "ROLE_MANAGER", "ROLE_ADMIN", "ROLE_FINANCE"}
    async with db.tx() as session:
        rows = (await session.scalars(select(Role).where(Role.name.in_(sorted(expected_roles))))).all()
        existing = {row.name for row in rows}
        missing = expected_roles - existing
        for role_name in sorted(missing):
            session.add(Role(name=role_name))


async def _cleanup_legacy_roles() -> None:
    legacy_to_prefixed = {
        "ADMIN": "ROLE_ADMIN",
        "EMPLOYEE": "ROLE_EMPLOYEE",
        "HR": "ROLE_HR",
        "MANAGER": "ROLE_MANAGER",
        "FINANCE": "ROLE_FINANCE",
    }
    relevant_names = sorted(set(legacy_to_prefixed) | set(legacy_to_prefixed.values()))
    async with db.tx() as session:
        rows = (await session.scalars(select(Role).where(Role.name.in_(relevant_names)))).all()
        by_name = {row.name: row for row in rows}

        for prefixed in legacy_to_prefixed.values():
            if prefixed not in by_name:
                created = Role(name=prefixed)
                session.add(created)
                await session.flush()
                by_name[prefixed] = created

        for legacy_name, prefixed_name in legacy_to_prefixed.items():
            legacy_role = by_name.get(legacy_name)
            prefixed_role = by_name.get(prefixed_name)
            if not legacy_role or not prefixed_role:
                continue

            assignments = (
                await session.scalars(select(UserRole).where(UserRole.role_id == legacy_role.id))
            ).all()
            for assignment in assignments:
                duplicate = await session.scalar(
                    select(UserRole).where(
                        UserRole.user_id == assignment.user_id,
                        UserRole.role_id == prefixed_role.id,
                        UserRole.project_id == assignment.project_id,
                    )
                )
                if duplicate:
                    await session.delete(assignment)
                else:
                    assignment.role_id = prefixed_role.id
            await session.delete(legacy_role)


async def _seed_system_projects() -> None:
    defaults = [
        {"project_code": "BENCH", "project_name": "Bench", "project_type": "IN_HOUSE", "is_active": True},
        {"project_code": "GLOBAL", "project_name": "Global", "project_type": "IN_HOUSE", "is_active": True},
    ]
    async with db.tx() as session:
        for project in defaults:
            existing = await session.scalar(select(Project).where(Project.project_code == project["project_code"]))
            if not existing:
                session.add(Project(**project))


@app.on_event("startup")
async def on_startup() -> None:
    settings = get_settings()
    await db.connect()
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_roles()
    await _cleanup_legacy_roles()
    await _seed_system_projects()
    await seed_master_data(db)
    if settings.enable_scheduler:
        start_scheduler(db=db, timezone=settings.scheduler_timezone)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    stop_scheduler()
    await db.disconnect()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
