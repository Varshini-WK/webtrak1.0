from pydantic import BaseModel, EmailStr


class HeadcountDistributionItem(BaseModel):
    department: str
    department_type: str
    designation: str
    total_headcount: int


class HeadcountDistributionPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[HeadcountDistributionItem]


class RoleWiseBilledItem(BaseModel):
    role: str
    department_type: str
    total_count: int
    billed_count: int
    billed_percent: float
    unbilled_count: int
    unbilled_percent: float


class RoleWiseBilledPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[RoleWiseBilledItem]


class ExperienceItem(BaseModel):
    emp_id: str | None
    email: EmailStr
    name: str
    department: str | None
    role: str | None
    department_type: str
    webknot_experience: str
    total_experience: str


class ExperiencePage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[ExperienceItem]


class DepartmentUtilizationItem(BaseModel):
    department: str
    head_count: int
    actual_billed: float
    utilization_percent: float
    buffer: float
    investment: float
    talent_pool: float


class DepartmentUtilizationPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[DepartmentUtilizationItem]


class BenchAgingItem(BaseModel):
    emp_id: str | None
    email: EmailStr
    name: str
    department: str | None
    bench_days: int | None


class BenchAgingPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[BenchAgingItem]


class SkillRatingItem(BaseModel):
    skill: str
    rating: int


class SkillInventoryItem(BaseModel):
    emp_id: str | None
    email: EmailStr
    name: str
    department: str | None
    role: str | None
    primary_skills: list[str]
    secondary_skills: list[SkillRatingItem]
    certifications: list[str]


class SkillInventoryPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[SkillInventoryItem]


class ContractDistributionItem(BaseModel):
    employment_type: str
    count: int
    workforce_percent: float


class ContractDistributionPage(BaseModel):
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    data: list[ContractDistributionItem]

