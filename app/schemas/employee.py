from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.domain.work_profile import DELIVERY_STATUS_VALUES, WORK_LOCATION_TYPE_VALUES, normalize_choice


class SecondarySkillRating(BaseModel):
    skill: str
    rating: int

    @field_validator("skill")
    @classmethod
    def validate_skill(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("skill is required")
        return cleaned

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        if value < 1 or value > 5:
            raise ValueError("rating must be between 1 and 5")
        return value


class UserOnboardCreate(BaseModel):
    email: EmailStr
    name: str
    user_type: Literal["FULLTIME", "INTERN", "CONSULTANT"]
    department: str
    delivery_status: str
    phone_number: str
    work_mode: str
    work_location_type: str
    role: str
    band_id: int
    doj: date | None = None
    doi: date | None = None
    internship_duration: int | None = None

    @field_validator("delivery_status", mode="before")
    @classmethod
    def validate_delivery_status(cls, value):
        return normalize_choice(value, DELIVERY_STATUS_VALUES, "delivery_status")

    @field_validator("work_location_type", mode="before")
    @classmethod
    def validate_work_location_type(cls, value):
        return normalize_choice(value, WORK_LOCATION_TYPE_VALUES, "work_location_type")

    @model_validator(mode="after")
    def validate_onboarding_dates(self) -> "UserOnboardCreate":
        if self.user_type == "INTERN":
            if self.doi is None:
                raise ValueError("doi is required for INTERN user_type")
            if self.internship_duration is None:
                raise ValueError("internship_duration is required for INTERN user_type")
            return self
        if self.doj is None:
            raise ValueError("doj is required for FULLTIME and CONSULTANT user_type")
        return self


class UserOnboardUpdate(BaseModel):
    email: EmailStr
    name: str
    yoe: int | None = None
    experience: str | None = None
    primary_skills: list[str] = Field(default_factory=list)
    secondary_skills: list[SecondarySkillRating] = Field(default_factory=list)
    work_location_type: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name is required")
        if len(cleaned) > 255:
            raise ValueError("name must be at most 255 characters")
        return cleaned

    @field_validator("work_location_type", mode="before")
    @classmethod
    def validate_work_location_type(cls, value):
        return normalize_choice(value, WORK_LOCATION_TYPE_VALUES, "work_location_type")


class OnboardUserResponse(BaseModel):
    emp_id: str
    email: EmailStr
    name: str
    status: str
    user_type: str
    work_location_type: str | None = None


class ProfileUpdateRequest(BaseModel):
    phone_number: str | None = None
    work_mode: str | None = None
    primary_skills: list[str] | None = None
    secondary_skills: list[SecondarySkillRating] | None = None
    experience: str | None = None
    work_location_type: str | None = None

    @field_validator("work_location_type", mode="before")
    @classmethod
    def validate_work_location_type(cls, value):
        return normalize_choice(value, WORK_LOCATION_TYPE_VALUES, "work_location_type")


class EmployeeProfileHrUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    user_status: str | None = None
    work_mode: str | None = None
    band_id: int | None = None
    primary_skills: list[str] | None = None
    secondary_skills: list[SecondarySkillRating] | None = None
    experience: str | None = None
    yoe: int | None = None
    work_location_type: str | None = None

    @field_validator("work_location_type", mode="before")
    @classmethod
    def validate_work_location_type(cls, value):
        return normalize_choice(value, WORK_LOCATION_TYPE_VALUES, "work_location_type")


class EmployeeProfileResponse(BaseModel):
    emp_id: str | None
    email: EmailStr
    name: str
    status: str
    user_type: str
    work_location_type: str | None = None
    department: str | None = None
    phone_number: str | None = None
    work_mode: str | None = None
    yoe: int | None = None
    experience: str | None = None
    primary_skills: list[str] = Field(default_factory=list)
    secondary_skills: list[SecondarySkillRating] = Field(default_factory=list)
    profile_photo: str | None = None
    personal_resume: str | None = None


class OnboardListItem(BaseModel):
    emp_id: str | None
    email: EmailStr
    name: str
    status: str
    user_type: str
    department: str | None = None


class OnboardListResponse(BaseModel):
    items: list[OnboardListItem]
    total: int
    page: int
    size: int


class RecentInvitedUserItem(BaseModel):
    emp_id: str | None
    email: EmailStr
    name: str
    status: str
    user_type: str
    department: str | None = None
    created_at: datetime


class RecentInvitedUsersResponse(BaseModel):
    items: list[RecentInvitedUserItem]
