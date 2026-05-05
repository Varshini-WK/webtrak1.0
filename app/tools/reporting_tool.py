from datetime import date

from app.schemas.attrition import (
    AttritionAverageTenureTable,
    AttritionCriticalSkillTable,
    AttritionManagerWiseTable,
    AttritionOverallPercentTable,
    AttritionRecordResponse,
    AttritionRegrettedTable,
    AttritionRoleWiseTable,
    AttritionUpsertRequest,
    AttritionVoluntaryInvoluntaryTable,
)
from app.schemas.reporting import (
    BenchAgingPage,
    DepartmentUtilizationPage,
    ExperiencePage,
    HeadcountDistributionPage,
    RoleWiseBilledPage,
    SkillInventoryPage,
    ContractDistributionPage,
)
from app.services.reporting_service import ReportingService


class ReportingTool:
    def __init__(self, db) -> None:
        self.service = ReportingService(db)

    async def workforce_headcount_distribution(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> HeadcountDistributionPage:
        return await self.service.get_headcount_distribution(page=page, size=size, search=search)

    async def workforce_role_wise_billed(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> RoleWiseBilledPage:
        return await self.service.get_role_wise_billed(page=page, size=size, search=search)

    async def workforce_experience(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> ExperiencePage:
        return await self.service.get_experience(page=page, size=size, search=search)

    async def workforce_utilization_by_department(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        as_of: date | None,
    ) -> DepartmentUtilizationPage:
        return await self.service.get_utilization_by_department(page=page, size=size, search=search, as_of=as_of)

    async def workforce_bench_aging(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        as_of: date | None,
    ) -> BenchAgingPage:
        return await self.service.get_bench_aging(page=page, size=size, search=search, as_of=as_of)

    async def skill_capacity_skill_inventory(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> SkillInventoryPage:
        return await self.service.get_skill_inventory(page=page, size=size, search=search)

    async def compliance_contract_distribution(
        self,
        *,
        page: int,
        size: int,
    ) -> ContractDistributionPage:
        return await self.service.get_contract_distribution(page=page, size=size)

    async def attrition_overall_percent(self, *, fy_start_year: int) -> AttritionOverallPercentTable:
        return await self.service.get_attrition_overall_percent(fy_start_year=fy_start_year)

    async def attrition_voluntary_involuntary(self, *, fy_start_year: int) -> AttritionVoluntaryInvoluntaryTable:
        return await self.service.get_attrition_voluntary_involuntary(fy_start_year=fy_start_year)

    async def attrition_role_wise(self, *, fy_start_year: int) -> AttritionRoleWiseTable:
        return await self.service.get_attrition_role_wise(fy_start_year=fy_start_year)

    async def attrition_manager_wise(self, *, fy_start_year: int) -> AttritionManagerWiseTable:
        return await self.service.get_attrition_manager_wise(fy_start_year=fy_start_year)

    async def attrition_critical_skill(self, *, fy_start_year: int) -> AttritionCriticalSkillTable:
        return await self.service.get_attrition_critical_skill(fy_start_year=fy_start_year)

    async def attrition_regretted(self, *, fy_start_year: int) -> AttritionRegrettedTable:
        return await self.service.get_attrition_regretted(fy_start_year=fy_start_year)

    async def attrition_average_tenure(self, *, fy_start_year: int) -> AttritionAverageTenureTable:
        return await self.service.get_attrition_average_tenure(fy_start_year=fy_start_year)

    async def attrition_upsert(
        self,
        *,
        actor_email: str,
        emp_id: str,
        payload: AttritionUpsertRequest,
    ) -> AttritionRecordResponse:
        return await self.service.upsert_attrition(actor_email=actor_email, emp_id=emp_id, payload=payload)

