from pydantic import BaseModel, EmailStr


class BgvUpsertRequest(BaseModel):
    consent_form_signed: bool
    identity: str | None = None
    employment_status: str
    reference_status: str
    mail_id_verified: EmailStr | None = None
    onboarding_form_status: str
    overall_status: str
    remarks: str | None = None


class BgvRecordResponse(BaseModel):
    employee_id: str | None
    name: str
    role: str | None
    level: str | None
    mail_id: EmailStr
    consent_form_signed: bool
    identity: str | None
    employment_status: str
    reference_status: str
    mail_id_verified: EmailStr | None
    onboarding_form_status: str
    overall_status: str
    remarks: str | None


class BgvDashboardItem(BaseModel):
    employee: str
    role: str | None
    consent: bool
    identity: str | None
    employment: str
    overall_status: str


class BgvDashboardPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[BgvDashboardItem]
