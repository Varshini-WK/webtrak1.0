from datetime import date, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class UserRequestCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_from_date: date = Field(validation_alias=AliasChoices("request_from_date", "requestFromDate"))
    request_to_date: date = Field(validation_alias=AliasChoices("request_to_date", "requestToDate"))
    request_type: str = Field(validation_alias=AliasChoices("request_type", "userRequestType", "requestType"))
    comments: str | None = None
    is_half_day: bool = Field(default=False, validation_alias=AliasChoices("is_half_day", "isHalfDay"))
    reference_file_url: str | None = Field(default=None, validation_alias=AliasChoices("reference_file_url", "referenceFileUrl"))
    manager_comp_off_email: EmailStr | None = Field(
        default=None,
        validation_alias=AliasChoices("manager_comp_off_email", "managerCompOffEmail"),
    )
    client_approval: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("client_approval", "clientApproval"),
    )


class UserRequestUpdate(UserRequestCreate):
    user_request_id: int = Field(validation_alias=AliasChoices("user_request_id", "userRequestId"))


class UserRequestStatusUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_request_id: int = Field(validation_alias=AliasChoices("user_request_id", "userRequestId"))
    user_request_status: str = Field(validation_alias=AliasChoices("user_request_status", "userRequestStatus"))
    message: str | None = None


class UserRequestDelete(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_request_id: int = Field(validation_alias=AliasChoices("user_request_id", "userRequestId"))


class UserRequestOut(BaseModel):
    id: int
    emp_email: EmailStr
    request_from_date: date
    request_to_date: date
    comments: str | None = None
    request_type: str
    status: str
    is_half_day: bool
    reference_file_url: str | None = None
    created_at: datetime
    updated_at: datetime


class UserRequestListResponse(BaseModel):
    current_page: int
    total_pages: int
    page_size: int
    total_elements: int
    data: list[UserRequestOut]
