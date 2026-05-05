from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TrainingCreateRequest(BaseModel):
    name: str
    category: Literal["PROFESSIONAL", "TECHNICAL", "SOFT_SKILLS"]
    type: Literal["MANDATORY", "OPTIONAL", "HYBRID"]
    description: str | None = None
    duration_days: int = Field(ge=1)


class TrainingUpdateRequest(BaseModel):
    name: str | None = None
    category: Literal["PROFESSIONAL", "TECHNICAL", "SOFT_SKILLS"] | None = None
    type: Literal["MANDATORY", "OPTIONAL", "HYBRID"] | None = None
    description: str | None = None
    duration_days: int | None = Field(default=None, ge=1)
    status: Literal["DRAFT", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = None


class TrainingOut(BaseModel):
    id: int
    name: str
    category: str
    type: str
    description: str | None
    duration_days: int
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

