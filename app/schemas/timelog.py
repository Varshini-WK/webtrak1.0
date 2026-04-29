from datetime import date, datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


TimeLogDecision = Literal["APPROVED", "REJECTED"]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class TimeLogCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_code: str = Field(min_length=1, validation_alias=AliasChoices("project_code", "projectCode"))
    log_date: date = Field(validation_alias=AliasChoices("log_date", "date"))
    hours: int = Field(ge=1, le=24, validation_alias=AliasChoices("hours", "loggedHours"))
    description: str | None = None


class TimeLogUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_code: str = Field(min_length=1, validation_alias=AliasChoices("project_code", "projectCode"))
    log_date: date = Field(validation_alias=AliasChoices("log_date", "date"))
    hours: int = Field(ge=1, le=24, validation_alias=AliasChoices("hours", "loggedHours"))
    description: str | None = None


class TimeLogStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    timelog_id: int = Field(validation_alias=AliasChoices("timelog_id", "timeLogId"))
    status: TimeLogDecision
    manager_comment: str | None = Field(default=None, validation_alias=AliasChoices("manager_comment", "approverComment"))


class TimeLogStatusBatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_email: EmailStr = Field(validation_alias=AliasChoices("employee_email", "employeeEmail"))
    project_code: str = Field(min_length=1, validation_alias=AliasChoices("project_code", "projectCode"))
    log_date: date = Field(validation_alias=AliasChoices("log_date", "date"))
    status: TimeLogDecision
    manager_comment: str | None = Field(default=None, validation_alias=AliasChoices("manager_comment", "approverComment"))


class TimeLogResponse(BaseModel):
    id: int
    employee_email: EmailStr
    project_code: str
    log_date: date
    hours: int
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, row) -> "TimeLogResponse":
        return cls(
            id=row.id,
            employee_email=row.employeeEmail,
            project_code=row.projectCode,
            log_date=row.logDate,
            hours=row.hours,
            description=row.description,
            status=row.status,
            created_at=row.createdAt,
            updated_at=row.updatedAt,
        )


class TimeLogListResponse(BaseModel):
    items: list[TimeLogResponse]
    total: int
    page: int
    size: int


class AddTimeLogRequestJava(BaseModel):
    employeeEmail: EmailStr | None = None
    projectCode: str = Field(min_length=1)
    description: str | None = None
    loggedHours: int = Field(ge=1, le=24)
    date: date


class UpdateTimeLogEntryRequestJava(BaseModel):
    timeLogId: int
    description: str | None = None
    loggedHours: int = Field(ge=1, le=24)
