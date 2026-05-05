from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Department(StrEnum):
    Developer = "Developer"
    AIML = "AI/ML"
    BusinessAnalyst = "Business Analyst"
    UIUX = "UI/UX"
    DevOps = "DevOps"
    Finance = "Finance"
    ProjectManager = "Project Manager"
    QualityAssurance = "Quality Assurance"
    Executive = "Executive"


# --- Band (selection list) ---


class BandListItem(BaseModel):
    id: int
    name: str
    # stream: str | None = None
    # designation: str | None = None


class DepartmentListItem(BaseModel):
    name: str


# --- KPI definitions ---


class KpiDefinitionResponse(BaseModel):
    id: int
    band_id: int
    department: str
    designation: str
    kpi_name: str
    weightage: Decimal
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KpiDefinitionCreate(BaseModel):
    band_id: int = Field(..., gt=0)
    department: Department
    designation: str = Field(..., min_length=1, max_length=255)
    kpi_name: str = Field(..., min_length=1, max_length=255)
    weightage: Decimal = Field(..., description="Between 5 and 100 inclusive")
    active: bool = True

    @field_validator("weightage")
    @classmethod
    def weightage_range(cls, v: Decimal) -> Decimal:
        f = float(v)
        if f < 5.0 or f > 100.0:
            raise ValueError("Weightage must be between 5 and 100")
        return v


class KpiDefinitionUpdate(BaseModel):
    band_id: int | None = Field(default=None, gt=0)
    department: Department | None = None
    designation: str | None = Field(default=None, min_length=1, max_length=255)
    kpi_name: str | None = Field(default=None, min_length=1, max_length=255)
    weightage: Decimal | None = None
    active: bool | None = None

    @field_validator("weightage")
    @classmethod
    def weightage_range(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        f = float(v)
        if f < 5.0 or f > 100.0:
            raise ValueError("Weightage must be between 5 and 100")
        return v


class PaginatedKpiDefinitions(BaseModel):
    data: list[KpiDefinitionResponse]
    current_page: int
    page_size: int
    total_element: int
    total_page: int


# --- Webknot values ---


class WebknotValueResponse(BaseModel):
    id: int
    title: str
    evaluation_criteria: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebknotValueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    evaluation_criteria: str | None = None
    active: bool = True


class WebknotValueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    evaluation_criteria: str | None = None
    active: bool | None = None


class PaginatedWebknotValues(BaseModel):
    data: list[WebknotValueResponse]
    current_page: int
    page_size: int
    total_element: int
    total_page: int


# --- Submission cycles ---


class SubmissionCycleResponse(BaseModel):
    id: int
    cycle_key: str
    scope: str
    window_start_at: datetime
    window_end_at: datetime | None
    manual_closed: bool
    updated_by: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubmissionCycleCreate(BaseModel):
    cycle_key: str = Field(..., min_length=1, max_length=7)
    scope: str | None = Field(default=None, max_length=16)
    window_start_at: datetime
    window_end_at: datetime | None = None
    manual_closed: bool = False
    updated_by: str | None = None


class SubmissionCycleUpdate(BaseModel):
    cycle_key: str | None = Field(default=None, min_length=1, max_length=7)
    scope: str | None = Field(default=None, max_length=16)
    window_start_at: datetime | None = None
    window_end_at: datetime | None = None
    manual_closed: bool | None = None
    updated_by: str | None = None


class PaginatedSubmissionCycles(BaseModel):
    data: list[SubmissionCycleResponse]
    current_page: int
    page_size: int
    total_element: int
    total_page: int


# --- Designations (read-only list) ---


class DesignationResponse(BaseModel):
    id: int
    name: str | None
    band_id: int | None
    department: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
