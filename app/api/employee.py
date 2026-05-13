import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.access import get_actor_email, get_actor_roles, require_any_role
from app.core.database import get_db
from app.domain.notification_types import NotificationType
from app.repositories.user_repository import UserRepository
from app.schemas.attrition import AttritionUpsertRequest
from app.schemas.common import GenericResponse
from app.schemas.employee import (
    EmployeeProfileHrUpdate,
    EmployeeProfileResponse,
    OnboardListResponse,
    OnboardUserResponse,
    ProfileUpdateRequest,
    UserOnboardCreate,
    UserOnboardUpdate,
)
from app.tools.employee_tool import EmployeeTool
from app.services.notification_service import NotificationService

router = APIRouter()

_LEGACY_AUTHENTICATED_ROLES = frozenset({"ROLE_HR", "ROLE_MANAGER", "ROLE_EMPLOYEE", "ROLE_ADMIN"})


def _require_email(request: Request) -> str:
    return get_actor_email(request)


@router.post("/user/onboard", response_model=GenericResponse)
async def create_user_onboard(payload: UserOnboardCreate, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    tool = EmployeeTool(db)
    result = await tool.create_user_onboard(payload)
    return GenericResponse(message="success", data=result.model_dump())


@router.put("/user/onboard", response_model=GenericResponse)
async def update_user_onboard(
    request: Request,
    user_data: str = Form(...),
    resume: UploadFile | None = File(default=None),
    reliving_letter: UploadFile | None = File(default=None),
    salary_slips: list[UploadFile] = File(default=[]),
    certifications: list[UploadFile] = File(default=[]),
    profile_photo: UploadFile | None = File(default=None),
    aadhaar: UploadFile | None = File(default=None),
    pan_card: UploadFile | None = File(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_EMPLOYEE","ROLE_ADMIN","ROLE_HR"})
    payload = UserOnboardUpdate.model_validate(json.loads(user_data))
    actor = get_actor_email(request)
    if str(payload.email).strip().lower() != actor.strip().lower():
        print("Cannot update onboarding for another user")
        print(payload.email)
        print(actor)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update onboarding for another user")
    tool = EmployeeTool(db)
    result = await tool.update_user_onboard(
        payload=payload,
        resume=resume,
        reliving_letter=reliving_letter,
        salary_slips=salary_slips,
        certifications=certifications,
        profile_photo=profile_photo,
        aadhaar=aadhaar,
        pan_card=pan_card,
    )
    return GenericResponse(message="success", data=result.model_dump())


@router.get("/user/recent-invited", response_model=GenericResponse)
async def get_recent_invited_users(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    tool = EmployeeTool(db)
    result = await tool.get_recent_invited_users()
    return GenericResponse(message="Recent invited employees fetched successfully", data=result.model_dump())


@router.get("/user/onboard", response_model=GenericResponse)
async def get_onboarded_users(
    request: Request,
    page: int = 0,
    size: int = 10,
    search: str | None = None,
    type: str | None = None,
    onboardingStatus: str | None = None,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR","ROLE_ADMIN"})
    tool = EmployeeTool(db)
    result = await tool.get_onboarded_users(
        page=page,
        size=size,
        search=search,
        user_type=type,
        onboarding_status=onboardingStatus,
    )
    return GenericResponse(message="all onboarded users fetched successfully", data=result.model_dump())


@router.get("/profile", response_model=GenericResponse)
async def get_profile(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _LEGACY_AUTHENTICATED_ROLES)
    email = _require_email(request)
    tool = EmployeeTool(db)
    result = await tool.get_profile(email)
    return GenericResponse(message="Profile fetched successfully", data=result.model_dump())


@router.put("/profile", response_model=GenericResponse)
async def update_profile(
    request: Request,
    body: str = Form(...),
    profilePic: UploadFile | None = File(default=None),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _LEGACY_AUTHENTICATED_ROLES)
    email = _require_email(request)
    payload = ProfileUpdateRequest.model_validate(json.loads(body))
    tool = EmployeeTool(db)
    result = await tool.update_profile(email=email, payload=payload, profile_pic=profilePic)
    return GenericResponse(message="Profile updated successfully", data=result.model_dump())


@router.get("/employee-profile/{empId}", response_model=GenericResponse)
async def get_employee_profile(empId: str, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR"})
    tool = EmployeeTool(db)
    result = await tool.get_employee_profile(empId)
    return GenericResponse(message="Employee profile fetched successfully", data=result.model_dump())


@router.put("/employee-profile/{empId}", response_model=GenericResponse)
async def update_employee_profile(
    empId: str,
    payload: EmployeeProfileHrUpdate,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR"})
    tool = EmployeeTool(db)
    result = await tool.update_employee_profile(empId, payload)
    return GenericResponse(message="Employee profile updated successfully", data=result.model_dump())


@router.get("/user", response_model=GenericResponse)
async def get_user(email: str | None = None, empId: str | None = None, db=Depends(get_db)) -> GenericResponse:
    tool = EmployeeTool(db)
    if email:
        result = await tool.get_profile(email)
        return GenericResponse(message="success", data=result.model_dump())
    if empId:
        result = await tool.get_employee_profile(empId)
        return GenericResponse(message="success", data=result.model_dump())
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide email or empId")


@router.post("/upload", response_model=GenericResponse)
async def upload_leave_excel(request: Request, file: UploadFile = File(...), db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    content = await file.read()
    result = await EmployeeTool(db).import_leave_data(content)
    actor = await UserRepository(db).get_by_email(get_actor_email(request).lower())
    if actor:
        await NotificationService(db).send_notification(
            receiver_id=actor.id,
            sender_id=None,
            notification_type=NotificationType.IMPORT_JOB_COMPLETED,
            title="Leave Import Completed",
            message=f"Processed={result.get('processed', 0)} Skipped={result.get('skipped', 0)}",
        )
    return GenericResponse(message="Leave data imported successfully", data=result)


@router.post("/upload-allocation", response_model=GenericResponse)
async def upload_allocation_excel(request: Request, file: UploadFile = File(...), db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    content = await file.read()
    result = await EmployeeTool(db).import_allocations_legacy(content, get_actor_roles(request))
    actor = await UserRepository(db).get_by_email(get_actor_email(request).lower())
    if actor:
        await NotificationService(db).send_notification(
            receiver_id=actor.id,
            sender_id=None,
            notification_type=NotificationType.IMPORT_JOB_COMPLETED,
            title="Allocation Import Completed",
            message=f"Completed={result.get('completed', 0)} Errors={len(result.get('errors', []))}",
        )
    return GenericResponse(message="Allocation data imported successfully", data=result)


@router.post("/upload/user-data", response_model=GenericResponse)
async def upload_user_data_excel(request: Request, file: UploadFile = File(...), db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    content = await file.read()
    result = await EmployeeTool(db).import_user_data(content)
    actor = await UserRepository(db).get_by_email(get_actor_email(request).lower())
    if actor:
        await NotificationService(db).send_notification(
            receiver_id=actor.id,
            sender_id=None,
            notification_type=NotificationType.IMPORT_JOB_COMPLETED,
            title="User Data Import Completed",
            message=f"Processed={result.get('processed', 0)} Skipped={result.get('skipped', 0)}",
        )
    return GenericResponse(message="User data imported successfully", data=result)


@router.post("/user/batch", response_model=GenericResponse)
async def upload_users_batch(request: Request, file: UploadFile = File(...), db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_ADMIN"})
    content = await file.read()
    result = await EmployeeTool(db).bulk_upload_users(content)
    actor = await UserRepository(db).get_by_email(get_actor_email(request).lower())
    if actor:
        await NotificationService(db).send_notification(
            receiver_id=actor.id,
            sender_id=None,
            notification_type=NotificationType.IMPORT_JOB_COMPLETED,
            title="User Batch Import Completed",
            message=f"Processed={result.get('processed', 0)}",
        )
    return GenericResponse(message="success", data=result)


@router.post("/user/offboard/{emp_id}", response_model=GenericResponse)
async def offboard_employee(
    emp_id: str,
    payload: AttritionUpsertRequest,
    request: Request,
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    actor_email = get_actor_email(request)
    result = await EmployeeTool(db).offboard_employee(actor_email=actor_email, emp_id=emp_id, payload=payload)
    return GenericResponse(message="employee offboarded successfully", data=result.model_dump())
