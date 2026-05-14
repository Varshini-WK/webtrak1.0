from datetime import date, time
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class TrainingCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    name: str
    category: Literal["PROFESSIONAL", "TECHNICAL", "SOFT_SKILLS"]
    type: Literal["MANDATORY", "OPTIONAL", "HYBRID"]
    description: str | None = None
    start_date: date = Field(validation_alias=AliasChoices("start_date", "startDate"))
    end_date: date = Field(validation_alias=AliasChoices("end_date", "endDate"))

    @model_validator(mode="after")
    def validate_date_range(self) -> "TrainingCreateRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TrainingUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    name: str | None = None
    category: Literal["PROFESSIONAL", "TECHNICAL", "SOFT_SKILLS"] | None = None
    type: Literal["MANDATORY", "OPTIONAL", "HYBRID"] | None = None
    description: str | None = None
    start_date: date | None = Field(default=None, validation_alias=AliasChoices("start_date", "startDate"))
    end_date: date | None = Field(default=None, validation_alias=AliasChoices("end_date", "endDate"))
    status: Literal["DRAFT", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "TrainingUpdateRequest":
        if self.start_date is not None and self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class TrainingOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    category: str
    type: str
    description: str | None
    start_date: date
    end_date: date
    status: str
    trainer_user_ids: list[int] = Field(default_factory=list)


class TrainerAssignRequest(BaseModel):
    trainer_user_ids: list[int] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    session_date: date
    start_time: time
    end_time: time
    mode: Literal["ONLINE", "OFFLINE", "HYBRID"]
    venue: str | None = None
    meeting_link: str | None = None

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "SessionCreateRequest":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        if self.mode in {"ONLINE", "HYBRID"} and not (self.meeting_link and self.meeting_link.strip()):
            raise ValueError("meeting_link is required for ONLINE/HYBRID")
        if self.mode in {"OFFLINE", "HYBRID"} and not (self.venue and self.venue.strip()):
            raise ValueError("venue is required for OFFLINE/HYBRID")
        return self


class SessionOut(BaseModel):
    id: int
    training_id: int
    session_date: date
    start_time: time
    end_time: time
    mode: str
    venue: str | None = None
    meeting_link: str | None = None


class ParticipantAssignRequest(BaseModel):
    user_ids: list[int] = Field(default_factory=list)
    department: str | None = None
    select_all: bool = False


class ParticipantOut(BaseModel):
    id: int
    training_id: int
    user_id: int
    participant_source: str
    enrollment_status: str | None = None


class ParticipantStatusUpdateRequest(BaseModel):
    enrollment_status: Literal["WITHDRAWN", "COMPLETED"]


class MaterialCreateRequest(BaseModel):
    title: str
    material_url: str
    visibility: Literal["HR_ONLY", "EMPLOYEE"] = "EMPLOYEE"


class AttendanceMarkRequest(BaseModel):
    user_id: int
    attendance_status: Literal["PRESENT", "ABSENT"]


class AssessmentCreateRequest(BaseModel):
    name: str
    description: str | None = None
    weight_percent: int = Field(ge=1, le=100)


class AssessmentCreateForm(BaseModel):
    name: str
    description: str | None = None
    weight_percent: int = Field(ge=1, le=100)


class ParticipantScoreUpsertRequest(BaseModel):
    user_id: int
    scores_json: dict[str, float]
    mark_completed: bool = False


class LearningAnalyticsOut(BaseModel):
    training_id: int
    enrolled_count: int
    completed_count: int
    average_score_percent: float
    average_attendance_percent: float

