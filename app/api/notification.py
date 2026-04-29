import asyncio
import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.access import get_actor_email, require_any_role
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.common import GenericResponse
from app.schemas.notification import AnnouncementCreateRequest
from app.services.notification_service import NotificationService
from app.services.notification_stream_service import get_notification_stream_service

router = APIRouter()

_AUTHENTICATED = frozenset({"ROLE_HR", "ROLE_MANAGER", "ROLE_EMPLOYEE", "ROLE_ADMIN", "ROLE_FINANCE"})


@router.get("/notifications", response_model=GenericResponse)
async def list_notifications(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=200),
    db=Depends(get_db),
) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    actor_email = get_actor_email(request)
    data = await NotificationService(db).list_notifications_for_actor(actor_email, page, size)
    return GenericResponse(message="success", data=data)


@router.put("/notifications/{notification_id}/read", response_model=GenericResponse)
async def mark_notification_read(notification_id: int, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    actor_email = get_actor_email(request)
    row = await NotificationService(db).mark_read_for_actor(actor_email, notification_id)
    return GenericResponse(message="success", data=row)


@router.put("/notifications/read-all", response_model=GenericResponse)
async def mark_all_notifications_read(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, _AUTHENTICATED)
    actor_email = get_actor_email(request)
    count = await NotificationService(db).mark_all_read_for_actor(actor_email)
    return GenericResponse(message="success", data={"updated": count})


@router.post("/notifications/announcement", response_model=GenericResponse)
async def create_announcement(payload: AnnouncementCreateRequest, request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    actor_email = get_actor_email(request)
    result = await NotificationService(db).announce(actor_email, payload.title, payload.message)
    return GenericResponse(message="success", data=result)


@router.get("/notifications/delete", response_model=GenericResponse)
async def delete_read_notifications(request: Request, db=Depends(get_db)) -> GenericResponse:
    require_any_role(request, {"ROLE_HR", "ROLE_ADMIN"})
    deleted = await NotificationService(db).delete_read_notifications()
    return GenericResponse(message="success", data={"deleted": deleted})


@router.get("/notifications/subscribe")
async def subscribe_notifications(request: Request, db=Depends(get_db)) -> StreamingResponse:
    require_any_role(request, _AUTHENTICATED)
    actor_email = get_actor_email(request)
    actor = await UserRepository(db).get_by_email(actor_email.lower())
    if not actor:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    stream = get_notification_stream_service()
    queue = await stream.subscribe(actor.id)

    async def event_gen():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    payload = {
                        "id": event.id,
                        "receiver_id": event.receiver_id,
                        "sender_id": event.sender_id,
                        "type": event.type,
                        "title": event.title,
                        "message": event.message,
                        "is_read": event.is_read,
                        "created_at": event.created_at,
                    }
                    yield f"event: notification\ndata: {json.dumps(payload)}\n\n"
                except TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
        finally:
            await stream.unsubscribe(actor.id, queue)

    return StreamingResponse(event_gen(), media_type="text/event-stream")

