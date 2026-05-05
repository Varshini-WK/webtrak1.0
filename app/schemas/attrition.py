from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class AttritionUpsertRequest(BaseModel):
    last_working_day: date
    separation_type: str = Field(..., description="VOLUNTARY or INVOLUNTARY")
    reason: str | None = None
    critical_skill: str | None = None
    is_regretted: bool = False


class AttritionRecordResponse(BaseModel):
    emp_id: str | None
    employee_name: str
    separation_type: str
    reason: str | None
    critical_skill: str | None
    is_regretted: bool
    last_working_day: date
    designation: str | None
    band_name: str | None
    band_role: str | None
    project_manager: str | None = Field(
        default=None,
        description="Comma-separated manager user IDs (users.id) on the employee's project at last working day.",
    )


# --- GET /reports/attrition/* : one response model per report table (5.1–5.6) ---


class AttritionFYPeriod(BaseModel):
    fy_start_year: int
    time_range: str = "April → March (Financial Year)"
    fy_april_start: date
    fy_march_end: date


class AttritionOverallPercentTable(BaseModel):
    """5.1 Overall Attrition %. Attrition % = (Number of Exits in FY / Total headcount in office) × 100."""

    fy_start_year: int
    time_range: str = "April → March (Financial Year)"
    fy_april_start: date
    fy_march_end: date
    number_of_exits: int
    attrition_percent: float


class AttritionVoluntaryInvoluntaryTable(BaseModel):
    """5.2 Voluntary vs Involuntary. Each exit must be VOLUNTARY or INVOLUNTARY (enforced on POST)."""

    voluntary_count: int
    involuntary_count: int
    total_count: int  # voluntary_count + involuntary_count


class AttritionRoleWiseItem(BaseModel):
    role_or_designation: str
    exit_count: int


class AttritionRoleWiseTable(BaseModel):
    """5.3 Role-wise attrition."""

    rows: list[AttritionRoleWiseItem]


class AttritionManagerWiseItem(BaseModel):
    reporting_manager: str = Field(
        ...,
        description="Comma-separated reporting manager display names (resolved from users.id stored on attritions.project_manager).",
    )
    exit_count: int


class AttritionManagerWiseTable(BaseModel):
    """5.3 Manager-wise attrition."""

    rows: list[AttritionManagerWiseItem]


class AttritionCriticalSkillItem(BaseModel):
    critical_skill: str
    exit_count: int


class AttritionCriticalSkillTable(BaseModel):
    """5.4 Critical skill attrition (HR-captured at exit)."""

    rows: list[AttritionCriticalSkillItem]


class AttritionRegrettedTable(BaseModel):
    """5.5 Regretted attrition."""

    total_regretted_exits: int
    percent_of_total_attrition: float


class AttritionTenureBucketItem(BaseModel):
    tenure_bucket: str
    range_days: str
    number_of_employees: int


class AttritionAverageTenureTable(BaseModel):
    """5.6 Average tenure (bucketed)."""

    buckets: list[AttritionTenureBucketItem]
    average_tenure_days: float | None
    tenure_unknown_employees: int


class AttritionFYReport(BaseModel):
    """FY attrition report: separate payloads per UI table (sections 5.1–5.6)."""

    fy_period: AttritionFYPeriod
    overall_attrition_percent: AttritionOverallPercentTable
    voluntary_vs_involuntary: AttritionVoluntaryInvoluntaryTable
    role_wise_attrition: AttritionRoleWiseTable
    manager_wise_attrition: AttritionManagerWiseTable
    critical_skill_attrition: AttritionCriticalSkillTable
    regretted_attrition: AttritionRegrettedTable
    average_tenure: AttritionAverageTenureTable
