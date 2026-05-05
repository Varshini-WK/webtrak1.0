"""Employment lifecycle values stored on ``users.status`` (string column)."""

from enum import Enum


class EmployeeStatus(str, Enum):
    INVITED = "INVITED"
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    OFFBOARDED = "OFFBOARDED"
