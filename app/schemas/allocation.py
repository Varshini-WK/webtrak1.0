from datetime import date, datetime
from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.domain.allocation_rules import (
    AllocationType,
    as_date,
    validate_allocated_hours,
    validate_allocation_type_for_project,
    validate_date_window,
    validate_locked_in_date,
    validate_staffing_project_allocation_type,
)
from app.domain.billing_status import normalize_billing_status
from app.domain.work_profile import WORK_LOCATION_TYPE_VALUES, normalize_choice


def _parse_day(v: date | datetime | str) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        # ISO date or datetime
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            y, m, d = v.split("-")
            return date(int(y), int(m), int(d))
        return datetime.fromisoformat(v.replace("Z", "+00:00")).date()
    raise TypeError(f"Unsupported date type: {type(v)}")


class AllocationCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_email: EmailStr = Field(validation_alias=AliasChoices("employee_email", "employeeEmail"))
    project_code: Annotated[str, Field(min_length=1, validation_alias=AliasChoices("project_code", "projectCode"))]
    role: str | None = None
    allocated_hours: Annotated[int, Field(ge=1, le=8, validation_alias=AliasChoices("allocated_hours", "allocatedHours"))]
    start_date: date = Field(validation_alias=AliasChoices("start_date", "startDate"))
    end_date: date | None = Field(default=None, validation_alias=AliasChoices("end_date", "endDate"))
    allocation_type: AllocationType = Field(
        default=AllocationType.DEPLOYABLE,
        validation_alias=AliasChoices("allocation_type", "allocationType"),
    )
    locked_in_date: date | None = Field(default=None, validation_alias=AliasChoices("locked_in_date", "lockedInDate"))
    is_manager: bool = Field(default=False, validation_alias=AliasChoices("is_manager", "isManager"))
    billing_status: str | None = Field(
        default=None,
        validation_alias=AliasChoices("billing_status", "billingStatus"),
    )
    work_location_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("work_location_type", "workLocationType"),
    )

    @field_validator("start_date", "end_date", "locked_in_date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        if v is None:
            return v
        return _parse_day(v)

    @field_validator("project_code")
    @classmethod
    def strip_project_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("work_location_type", mode="before")
    @classmethod
    def validate_work_location_type(cls, v):
        return normalize_choice(v, WORK_LOCATION_TYPE_VALUES, "work_location_type")

    @field_validator("billing_status", mode="before")
    @classmethod
    def validate_billing_status(cls, v):
        return normalize_billing_status(v)

    @model_validator(mode="after")
    def validate_rules(self) -> "AllocationCreateRequest":
        validate_date_window(self.start_date, self.end_date)
        validate_allocated_hours(self.allocated_hours)
        validate_locked_in_date(self.start_date, self.end_date, self.locked_in_date, self.allocation_type)
        return self

    def validate_against_project_type(self, project_type: str) -> None:
        validate_allocation_type_for_project(self.allocation_type, project_type)
        validate_staffing_project_allocation_type(self.allocation_type, project_type)


class AllocationUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    employee_email: EmailStr = Field(validation_alias=AliasChoices("employee_email", "employeeEmail"))
    project_code: Annotated[str, Field(min_length=1, validation_alias=AliasChoices("project_code", "projectCode"))]
    role: str | None = None
    allocated_hours: Annotated[int, Field(ge=1, le=8, validation_alias=AliasChoices("allocated_hours", "allocatedHours"))]
    start_date: date | None = Field(default=None, validation_alias=AliasChoices("start_date", "startDate"))
    end_date: date | None = Field(default=None, validation_alias=AliasChoices("end_date", "endDate"))
    allocation_type: AllocationType | None = Field(default=None, validation_alias=AliasChoices("allocation_type", "allocationType"))
    locked_in_date: date | None = Field(default=None, validation_alias=AliasChoices("locked_in_date", "lockedInDate"))
    is_manager: bool = Field(default=False, validation_alias=AliasChoices("is_manager", "isManager"))
    billing_status: str | None = Field(
        default=None,
        validation_alias=AliasChoices("billing_status", "billingStatus"),
    )
    work_location_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("work_location_type", "workLocationType"),
    )

    @field_validator("start_date", "end_date", "locked_in_date", mode="before")
    @classmethod
    def coerce_dates(cls, v):
        if v is None:
            return v
        return _parse_day(v)

    @field_validator("project_code")
    @classmethod
    def strip_project_code(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("work_location_type", mode="before")
    @classmethod
    def validate_work_location_type(cls, v):
        return normalize_choice(v, WORK_LOCATION_TYPE_VALUES, "work_location_type")

    @field_validator("billing_status", mode="before")
    @classmethod
    def validate_billing_status(cls, v):
        return normalize_billing_status(v)

    def resolved_start(self, fallback: date) -> date:
        return self.start_date if self.start_date is not None else fallback

    def resolved_end(self) -> date | None:
        return self.end_date

    def resolved_type(self, fallback: AllocationType) -> AllocationType:
        return self.allocation_type if self.allocation_type is not None else fallback


class AllocationRequestJava(BaseModel):
    employeeEmail: EmailStr
    projectCode: Annotated[str, Field(min_length=1)]
    role: str | None = None
    allocatedHours: Annotated[int, Field(ge=1, le=8)]
    startDate: date | None = None
    endDate: date | None = None
    allocationType: AllocationType | None = AllocationType.DEPLOYABLE
    lockedInDate: date | None = None
    isManager: bool = False

    @field_validator("startDate", "endDate", "lockedInDate", mode="before")
    @classmethod
    def coerce_java_dates(cls, v):
        if v is None:
            return v
        if isinstance(v, str) and len(v) == 10 and v[2] == "-" and v[5] == "-":
            d, m, y = v.split("-")
            return date(int(y), int(m), int(d))
        return _parse_day(v)

    @field_validator("projectCode")
    @classmethod
    def strip_project_code_java(cls, v: str) -> str:
        return v.strip().upper()


class BatchAllocationRow(BaseModel):
    project_code: Annotated[str, Field(min_length=1)]
    employee_email: EmailStr
    role: str = Field(min_length=1)
    allocated_hours: Annotated[int, Field(ge=1, le=8)]

    @field_validator("project_code")
    @classmethod
    def strip_project_code(cls, v: str) -> str:
        return v.strip().upper()


class AllocationResponse(BaseModel):
    id: int
    user_id: int
    project_code: str
    role: str | None
    allocated_hours: int
    start_date: date
    end_date: date | None
    is_active: bool
    allocation_type: str
    locked_in_date: date | None
    billing_status: str | None = None
    work_location_type: str | None = None

    @classmethod
    def from_record(cls, row) -> "AllocationResponse":
        raw_type = getattr(row, "allocationType", None)
        if raw_type is None:
            type_str = AllocationType.DEPLOYABLE.value
        elif hasattr(raw_type, "value"):
            type_str = raw_type.value
        else:
            type_str = str(raw_type)
        return cls(
            id=row.id,
            user_id=row.userId,
            project_code=row.projectCode,
            role=row.role,
            allocated_hours=row.allocatedHours,
            start_date=as_date(row.startDate) or date.today(),
            end_date=as_date(row.endDate) if row.endDate else None,
            is_active=row.isActive,
            allocation_type=type_str,
            locked_in_date=as_date(row.lockedInDate) if getattr(row, "lockedInDate", None) else None,
            billing_status=getattr(row, "billingStatus", None),
            work_location_type=getattr(row, "workLocationType", None),
        )


class UserAllocationItem(BaseModel):
    project_name: str
    manager_name: str
    allocated_hours: int


class AllocationListMeta(BaseModel):
    current_page: int
    total_pages: int
    page_size: int
    total_elements: int


class AllocationListResponse(BaseModel):
    current_page: int
    total_pages: int
    page_size: int
    total_elements: int
    allocations: list[AllocationResponse]


class ForecastAllocationResponse(BaseModel):
    current_page: int
    total_pages: int
    page_size: int
    total_elements: int
    allocations: list[AllocationResponse]


class AllocationRoleItem(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


__all__ = [
    "AllocationCreateRequest",
    "AllocationRuleError",
    "AllocationResponse",
    "AllocationUpdateRequest",
    "BatchAllocationRow",
    "ForecastAllocationResponse",
    "AllocationListResponse",
    "AllocationRoleItem",
    "UserAllocationItem",
]
