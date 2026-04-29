from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class CreateAllocationExtensionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_email: EmailStr = Field(validation_alias=AliasChoices("user_email", "userEmail"))
    project_code: str = Field(min_length=1, validation_alias=AliasChoices("project_code", "projectCode"))
    requested_end_date: date = Field(validation_alias=AliasChoices("requested_end_date", "requestedEndDate"))
    reason: str | None = None


class UpdateAllocationExtensionStatusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: int = Field(validation_alias=AliasChoices("request_id", "requestId"))
    status: str


class AllocationExtensionRequestOut(BaseModel):
    id: int
    employee_name: str
    employee_email: EmailStr
    project_code: str
    project_name: str
    current_end_date: date
    requested_end_date: date
    reason: str | None = None
    requested_by_name: str
    status: str
    created_at: datetime


class AllocationExtensionRequestListResponse(BaseModel):
    current_page: int
    total_pages: int
    page_size: int
    total_elements: int
    data: list[AllocationExtensionRequestOut]
