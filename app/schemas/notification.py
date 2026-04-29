from datetime import datetime

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: int
    receiver_id: int | None
    sender_id: int | None
    type: str
    title: str
    message: str | None
    is_read: bool
    created_at: datetime


class NotificationPage(BaseModel):
    current_page: int
    total_pages: int
    page_size: int
    total_elements: int
    data: list[NotificationItem]


class AnnouncementCreateRequest(BaseModel):
    title: str
    message: str

