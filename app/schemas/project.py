from enum import Enum
from datetime import date

from pydantic import BaseModel, Field


class ProjectTypeEnum(str, Enum):
    IN_HOUSE = "IN_HOUSE"
    STAFFING = "STAFFING"
    PRODUCT = "PRODUCT"


class CreateProjectRequest(BaseModel):
    project_code: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    project_type: ProjectTypeEnum


class ProjectResponse(BaseModel):
    project_code: str
    project_name: str
    project_type: ProjectTypeEnum
    is_active: bool


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
