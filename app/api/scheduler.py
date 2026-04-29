from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.access import require_any_role
from app.core.database import get_db
from app.core.settings import get_settings
from app.schemas.common import GenericResponse
from app.services.scheduled_jobs_service import ScheduledJobsService

router = APIRouter()


@router.post("/scheduler/run-all", response_model=GenericResponse)
async def run_all_scheduler_jobs(request: Request, db=Depends(get_db)) -> GenericResponse:
    settings = get_settings()
    if settings.app_env.strip().lower() == "prod":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scheduler run-all is blocked in production")

    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    summary = await ScheduledJobsService(db).run_all_jobs()
    return GenericResponse(message="Scheduler jobs executed", data=summary)

