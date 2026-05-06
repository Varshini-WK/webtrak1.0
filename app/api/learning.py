from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.access import get_actor_email, get_actor_roles, require_any_role
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.common import GenericResponse
from app.schemas.learning import (
    AttendanceMarkRequest,
    ParticipantScoreUpsertRequest,
    ParticipantAssignRequest,
    ParticipantStatusUpdateRequest,
    SessionCreateRequest,
    TrainerAssignRequest,
    TrainingCreateRequest,
    TrainingUpdateRequest,
)
from app.services.learning_service import LearningService

router = APIRouter()


async def _actor_user_id(request: Request, db) -> int:
    actor = await UserRepository(db).get_by_email(get_actor_email(request).strip().lower())
    if not actor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor user not found")
    return int(actor.id)


@router.post("/trainings", response_model=GenericResponse)
async def create_training(payload: TrainingCreateRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.create_training(payload, actor_user_id=await _actor_user_id(request, db), actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.put("/trainings/{training_id}", response_model=GenericResponse)
async def update_training(training_id: int, payload: TrainingUpdateRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.update_training(training_id, payload, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.get("/trainings", response_model=GenericResponse)
async def list_trainings(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.list_trainings(actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/trainers", response_model=GenericResponse)
async def assign_trainers(training_id: int, payload: TrainerAssignRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.assign_trainers(training_id, payload.trainer_user_ids, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.delete("/trainings/{training_id}/trainers/{trainer_user_id}", response_model=GenericResponse)
async def remove_trainer(training_id: int, trainer_user_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.remove_trainer(training_id, trainer_user_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/sessions", response_model=GenericResponse)
async def create_session(training_id: int, payload: SessionCreateRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.create_session(training_id, payload, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.get("/trainings/{training_id}/sessions", response_model=GenericResponse)
async def list_sessions(training_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.list_sessions(training_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/participants", response_model=GenericResponse)
async def assign_participants(training_id: int, payload: ParticipantAssignRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.assign_participants(training_id, payload, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.delete("/trainings/{training_id}/participants/{user_id}", response_model=GenericResponse)
async def remove_participant(training_id: int, user_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.remove_participant(training_id, user_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.patch("/trainings/{training_id}/participants/{user_id}", response_model=GenericResponse)
async def update_participant_status(
    training_id: int,
    user_id: int,
    payload: ParticipantStatusUpdateRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.update_participant_status(
        training_id,
        user_id,
        payload.enrollment_status,
        actor_roles=get_actor_roles(request),
    )
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/enroll", response_model=GenericResponse)
async def self_enroll(training_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    actor_id = await _actor_user_id(request, db)
    result = await service.self_enroll(training_id, actor_user_id=actor_id)
    return GenericResponse(message="success", data=result)


@router.get("/trainings/open", response_model=GenericResponse)
async def list_open_trainings(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.list_open_trainings_for_employee()
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/materials", response_model=GenericResponse)
async def add_material(
    training_id: int,
    request: Request,
    title: str = Form(...),
    visibility: Literal["HR_ONLY", "EMPLOYEE"] = Form("EMPLOYEE"),
    material_file: UploadFile = File(...),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.add_material(
        training_id,
        title=title,
        visibility=visibility,
        material_file=material_file,
        actor_roles=get_actor_roles(request),
    )
    return GenericResponse(message="success", data=result)


@router.get("/trainings/{training_id}/materials", response_model=GenericResponse)
async def list_materials(training_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.list_materials(training_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/sessions/{training_session_id}/attendance", response_model=GenericResponse)
async def mark_attendance(
    training_id: int,
    training_session_id: int,
    payload: AttendanceMarkRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.mark_attendance(
        training_id,
        training_session_id,
        payload,
        actor_user_id=await _actor_user_id(request, db),
        actor_roles=get_actor_roles(request),
    )
    return GenericResponse(message="success", data=result)


@router.get("/trainings/{training_id}/sessions/{training_session_id}/attendance", response_model=GenericResponse)
async def list_session_attendance(training_id: int, training_session_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.list_session_attendance(training_id, training_session_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/assessments", response_model=GenericResponse)
async def create_assessment(
    training_id: int,
    request: Request,
    name: str = Form(...),
    description: str | None = Form(default=None),
    weight_percent: int = Form(...),
    assessment_file: UploadFile = File(...),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.create_assessment(
        training_id,
        name=name,
        description=description,
        weight_percent=weight_percent,
        assessment_file=assessment_file,
        actor_roles=get_actor_roles(request),
    )
    return GenericResponse(message="success", data=result)


@router.get("/trainings/{training_id}/assessments", response_model=GenericResponse)
async def list_assessments(training_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_MANAGER", "ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.list_assessments(training_id)
    return GenericResponse(message="success", data=result)


@router.post("/trainings/{training_id}/scores", response_model=GenericResponse)
async def upsert_participant_scores(
    training_id: int,
    payload: ParticipantScoreUpsertRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.upsert_participant_scores(training_id, payload, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)


@router.get("/trainings/{training_id}/analytics", response_model=GenericResponse)
async def get_training_analytics(training_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    service = LearningService(db)
    result = await service.get_training_analytics(training_id, actor_roles=get_actor_roles(request))
    return GenericResponse(message="success", data=result)

