from datetime import datetime

from pydantic import BaseModel, Field


class PolicyCreateRequest(BaseModel):
    title: str
    description: str | None = None
    deadline_at: datetime | None = None


class PolicyPublishRequest(BaseModel):
    send_to_all: bool = False
    department_filters: list[str] = Field(default_factory=list)
    role_filters: list[str] = Field(default_factory=list)
    user_ids: list[int] = Field(default_factory=list)
    delivery_channel: str = "BOTH"


class PolicyListItem(BaseModel):
    policy_id: int
    title: str
    status: str
    deadline_at: datetime | None = None
    sent_at: datetime | None = None
    viewed_at: datetime | None = None
    signed_at: datetime | None = None
    signed_file_url: str | None = None


class PolicyRecipientItem(BaseModel):
    user_id: int
    employee_name: str
    email: str
    department: str | None
    role: str | None
    status: str
    sent_at: datetime | None
    viewed_at: datetime | None
    signed_at: datetime | None
    signed_file_url: str | None


class PolicyComplianceReport(BaseModel):
    policy_id: int
    title: str
    deadline_at: datetime | None
    total_recipients: int
    sent_count: int
    viewed_count: int
    signed_count: int
    pending_count: int
    signed_percentage: float
    recipients: list[PolicyRecipientItem]
