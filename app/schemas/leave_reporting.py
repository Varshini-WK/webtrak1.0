from datetime import date

from pydantic import BaseModel, EmailStr


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

