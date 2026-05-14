from datetime import date

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class LeaveDetailsResponse(BaseModel):
    from_date: date
    to_date: date
    is_half_day: bool
    leave_count: float


class LeaveSummaryItem(BaseModel):
    name: str
    email: EmailStr
    emp_id: str | None
    role: str
    type: str
    band: str
    leaves: float
    lop: float
    leave_details: list[LeaveDetailsResponse]


class LeaveSummaryPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[LeaveSummaryItem]


class LeaveDayEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    leave_date: date = Field(validation_alias=AliasChoices("leave_date", "leaveDate", "date"))
    value: float


class EmployeeAttendanceLeaveRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(validation_alias=AliasChoices("user_id", "userId"))
    emp_id: str | None = Field(default=None, validation_alias=AliasChoices("emp_id", "empId"))
    email: str
    leave_days_taken: float = Field(
        validation_alias=AliasChoices("leave_days_taken", "leaveDaysTaken"),
        description="Sum of leave deductions in the date range.",
    )
    leave_dates: list[LeaveDayEntry]
    total_attendance_days: float = Field(
        validation_alias=AliasChoices("total_attendance_days", "totalAttendanceDays"),
        description="Working weekdays in range minus leave_days_taken (not below 0).",
    )
    weekday_days_with_timelog: int = Field(
        validation_alias=AliasChoices("weekday_days_with_timelog", "weekdayDaysWithTimelog"),
        description="Distinct weekdays with at least one SUBMITTED or APPROVED timelog.",
    )


class AttendanceLeaveReportPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_date: date = Field(validation_alias=AliasChoices("from_date", "fromDate"))
    to_date: date = Field(validation_alias=AliasChoices("to_date", "toDate"))
    working_weekdays_in_range: int = Field(validation_alias=AliasChoices("working_weekdays_in_range", "workingWeekdaysInRange"))
    current_page: int = Field(validation_alias=AliasChoices("current_page", "currentPage"))
    total_page: int = Field(validation_alias=AliasChoices("total_page", "totalPage"))
    page_size: int = Field(validation_alias=AliasChoices("page_size", "pageSize"))
    total_element: int = Field(validation_alias=AliasChoices("total_element", "totalElement"))
    employees: list[EmployeeAttendanceLeaveRow]

