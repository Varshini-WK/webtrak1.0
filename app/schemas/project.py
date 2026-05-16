from datetime import date
from enum import Enum

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class ProjectTypeEnum(str, Enum):
    IN_HOUSE = "IN_HOUSE"
    STAFFING = "STAFFING"
    PRODUCT = "PRODUCT"


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    project_name: str = Field(min_length=1, validation_alias=AliasChoices("project_name", "projectName"))
    project_type: ProjectTypeEnum
    client_name: str = Field(min_length=1, validation_alias=AliasChoices("client_name", "clientName"))
    account_manager_email: EmailStr = Field(
        validation_alias=AliasChoices("account_manager_email", "accountManagerEmail"),
    )
    project_code: str | None = Field(
        default=None,
        min_length=1,
        validation_alias=AliasChoices("project_code", "projectCode"),
        description="Optional manual override; when omitted, a unique P###_SLUG code is generated from the client name.",
    )


class ProjectResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_code: str
    project_name: str
    project_type: ProjectTypeEnum
    is_active: bool
    client_name: str | None = None
    account_manager_email: str | None = Field(default=None, validation_alias=AliasChoices("account_manager_email", "accountManagerEmail"))
    account_manager_name: str | None = Field(default=None, validation_alias=AliasChoices("account_manager_name", "accountManagerName"))


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    size: int


class ProjectSimpleListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


class ProjectCodeNameResponse(BaseModel):
    project_code: str
    project_name: str
    role: str | None = None
    allocated_hours: int | None = None
    start_date: date | None = None


class ProjectWithEmployeesResponse(BaseModel):
    project_code: str
    project_name: str
    project_type: ProjectTypeEnum
    employees: list[dict]


class ManagerProjectsResponse(BaseModel):
    manager_email: str
    manager_name: str
    projects: list[ProjectWithEmployeesResponse]


class ManagerTeamOnLeaveProjectItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_code: str = Field(validation_alias=AliasChoices("project_code", "projectCode"))
    project_name: str = Field(validation_alias=AliasChoices("project_name", "projectName"))


class ManagerTeamOnLeaveMember(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    emp_id: str | None = Field(default=None, validation_alias=AliasChoices("emp_id", "empId"))
    email: str
    name: str
    leave_units_today: float = Field(
        validation_alias=AliasChoices("leave_units_today", "leaveUnitsToday"),
        description="Sum of DEDUCT leave_transactions for the reference date (e.g. 0.5 half-day).",
    )
    projects: list[ManagerTeamOnLeaveProjectItem]


class ManagerTeamOnLeaveTodayResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    as_of_date: date = Field(validation_alias=AliasChoices("as_of_date", "asOfDate"))
    manager_email: str
    manager_name: str
    team_on_leave: list[ManagerTeamOnLeaveMember] = Field(
        validation_alias=AliasChoices("team_on_leave", "teamOnLeave"),
    )
