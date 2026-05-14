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
