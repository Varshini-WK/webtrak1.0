import json

from fastapi import APIRouter, Depends, File, Form, UploadFile, Request

from app.api.access import get_actor_email, require_any_role
from app.core.database import get_db
from app.schemas.common import GenericResponse
from app.schemas.policy import PolicyCreateRequest, PolicyPublishRequest
from app.tools.policy_tool import PolicyTool

router = APIRouter()


@router.post("/policies", response_model=GenericResponse)
async def create_policy(
    request: Request,
    payload: str = Form(...),
    document: UploadFile = File(...),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    actor_email = get_actor_email(request)
    req = PolicyCreateRequest.model_validate(json.loads(payload))
    result = await PolicyTool(db).create_policy(actor_email=actor_email, payload=req, document=document)
    return GenericResponse(message="policy created successfully", data=result)


@router.post("/policies/{policy_id}/publish", response_model=GenericResponse)
async def publish_policy(policy_id: int, payload: PolicyPublishRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    actor_email = get_actor_email(request)
    result = await PolicyTool(db).publish_policy(actor_email=actor_email, policy_id=policy_id, payload=payload)
    return GenericResponse(message="policy published successfully", data=result)


@router.get("/policies/my", response_model=GenericResponse)
async def my_policies(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_HR", "ROLE_ADMIN", "ROLE_MANAGER", "ROLE_FINANCE"})
    actor_email = get_actor_email(request)
    result = await PolicyTool(db).list_my_policies(actor_email=actor_email)
    return GenericResponse(message="my policies fetched successfully", data=[row.model_dump() for row in result])


@router.post("/policies/{policy_id}/viewed", response_model=GenericResponse)
async def viewed_policy(policy_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_HR", "ROLE_ADMIN", "ROLE_MANAGER", "ROLE_FINANCE"})
    actor_email = get_actor_email(request)
    result = await PolicyTool(db).mark_viewed(actor_email=actor_email, policy_id=policy_id)
    return GenericResponse(message="policy viewed status updated", data=result)


@router.post("/policies/{policy_id}/signed-copy", response_model=GenericResponse)
async def upload_signed_copy(
    policy_id: int,
    request: Request,
    signed_copy: UploadFile = File(...),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE", "ROLE_HR", "ROLE_ADMIN", "ROLE_MANAGER", "ROLE_FINANCE"})
    actor_email = get_actor_email(request)
    result = await PolicyTool(db).upload_signed_copy(actor_email=actor_email, policy_id=policy_id, signed_copy=signed_copy)
    return GenericResponse(message="signed copy uploaded successfully", data=result)


@router.get("/policies/{policy_id}/compliance", response_model=GenericResponse)
async def policy_compliance(policy_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await PolicyTool(db).get_policy_compliance(policy_id=policy_id)
    return GenericResponse(message="policy compliance fetched successfully", data=result.model_dump())


@router.get("/policies/{policy_id}/signed-documents", response_model=GenericResponse)
async def policy_signed_documents(policy_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await PolicyTool(db).list_signed_documents(policy_id=policy_id)
    return GenericResponse(message="policy signed documents fetched successfully", data=result)


@router.get("/policies/{policy_id}/signed-documents/export", response_model=GenericResponse)
async def policy_signed_documents_export(policy_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    result = await PolicyTool(db).export_signed_documents(policy_id=policy_id)
    return GenericResponse(message="policy signed documents export prepared", data=result)
