from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from fastapi import HTTPException, status

from app.domain.allocation_rules import BENCH_PROJECT_CODE
from app.domain.billing_status import is_talent_pool_billing
from app.repositories.attrition_repository import AttritionRepository
from app.repositories.reporting_repository import ReportingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.attrition import (
    AttritionAverageTenureTable,
    AttritionCriticalSkillItem,
    AttritionCriticalSkillTable,
    AttritionFYPeriod,
    AttritionFYReport,
    AttritionManagerWiseItem,
    AttritionManagerWiseTable,
    AttritionOverallPercentTable,
    AttritionRecordResponse,
    AttritionRegrettedTable,
    AttritionRoleWiseItem,
    AttritionRoleWiseTable,
    AttritionTenureBucketItem,
    AttritionUpsertRequest,
    AttritionVoluntaryInvoluntaryTable,
)
from app.schemas.reporting import (
    ContractDistributionItem,
    ContractDistributionPage,
    ExperienceItem,
    ExperiencePage,
    SkillInventoryItem,
    SkillInventoryPage,
    SkillRatingItem,
    BenchAgingItem,
    BenchAgingPage,
    DepartmentUtilizationItem,
    DepartmentUtilizationPage,
    HeadcountDistributionItem,
    HeadcountDistributionPage,
    RoleWiseBilledItem,
    RoleWiseBilledPage,
)


def _normalize_department_type(value: str | None) -> str:
    token = (value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if token in {"DELIVERABLE"}:
        return "DELIVERABLE"
    if token in {"NON_DELIVERABLE", "NONDELIVERABLE"}:
        return "NON_DELIVERABLE"
    return "UNKNOWN"


def _format_year_month(total_months: int) -> str:
    years = max(0, total_months) // 12
    months = max(0, total_months) % 12
    return f"{years}Y {months}M"


def _months_between(start: date, end: date) -> int:
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def _normalize_secondary_skills(raw: Any) -> list[SkillRatingItem]:
    if not isinstance(raw, list):
        return []
    items: list[SkillRatingItem] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        skill = entry.get("skill")
        rating = entry.get("rating")
        if not isinstance(skill, str) or not skill.strip():
            continue
        if not isinstance(rating, int):
            continue
        items.append(SkillRatingItem(skill=skill.strip(), rating=rating))
    return items


@dataclass
class _Page:
    current_page: int
    total_page: int
    page_size: int
    total_element: int
    start: int
    end: int


def _page_bounds(*, page: int, size: int, total: int) -> _Page:
    start = page * size
    end = start + size
    total_pages = 0 if total == 0 else (total + size - 1) // size
    return _Page(
        current_page=page,
        total_page=total_pages,
        page_size=size,
        total_element=total,
        start=start,
        end=end,
    )


class ReportingService:
    _ACTIVE_STATUSES = ["ACTIVE", "ONBOARDING", "INVITED"]
    _BILLED_STATUSES = {"BILLED", "BUFFER"}
    _UNBILLED_STATUSES = {"BENCH", "INVESTMENT", "TALENT_POOL"}
    _MAX_DAILY_HOURS = 8.0

    _SEPARATION_VOLUNTARY = "VOLUNTARY"
    _SEPARATION_INVOLUNTARY = "INVOLUNTARY"

    def __init__(self, db) -> None:
        self.repo = ReportingRepository(db)
        self.attrition_repo = AttritionRepository(db)
        self.user_repo = UserRepository(db)

    async def get_headcount_distribution(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> HeadcountDistributionPage:
        users = await self.repo.list_users_for_workforce_overview(search=search, statuses=self._ACTIVE_STATUSES)
        grouped: dict[tuple[str, str, str], int] = defaultdict(int)
        for user in users:
            department = (user.department or "UNKNOWN").strip() or "UNKNOWN"
            designation = (user.role or "UNKNOWN").strip() or "UNKNOWN"
            department_type = _normalize_department_type(user.delivery_status)
            grouped[(department, department_type, designation)] += 1

        items = [
            HeadcountDistributionItem(
                department=department,
                department_type=department_type,
                designation=designation,
                total_headcount=count,
            )
            for (department, department_type, designation), count in grouped.items()
        ]
        items.sort(key=lambda x: (x.department, x.department_type, x.designation))

        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        return HeadcountDistributionPage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=paged,
        )

    async def get_role_wise_billed(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> RoleWiseBilledPage:
        users = await self.repo.list_users_for_workforce_overview(search=search, statuses=self._ACTIVE_STATUSES)
        allocations = await self.repo.list_active_allocation_billing_statuses()

        billing_by_user: dict[int, set[str]] = defaultdict(set)
        for user_id, billing_status in allocations:
            status_token = (billing_status or "").strip().upper().replace("-", "_").replace(" ", "_")
            if status_token:
                billing_by_user[int(user_id)].add(status_token)

        grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"total": 0, "billed": 0, "unbilled": 0})
        for user in users:
            role = (user.role or "UNKNOWN").strip() or "UNKNOWN"
            department_type = _normalize_department_type(user.delivery_status)
            key = (role, department_type)
            grouped[key]["total"] += 1

            statuses = billing_by_user.get(int(user.id), set())
            if statuses & self._BILLED_STATUSES:
                grouped[key]["billed"] += 1
            elif statuses & self._UNBILLED_STATUSES:
                grouped[key]["unbilled"] += 1

        items: list[RoleWiseBilledItem] = []
        for (role, department_type), agg in grouped.items():
            total = int(agg["total"])
            billed = int(agg["billed"])
            unbilled = int(agg["unbilled"])
            billed_percent = round((billed * 100.0 / total), 2) if total else 0.0
            unbilled_percent = round((unbilled * 100.0 / total), 2) if total else 0.0
            items.append(
                RoleWiseBilledItem(
                    role=role,
                    department_type=department_type,
                    total_count=total,
                    billed_count=billed,
                    billed_percent=billed_percent,
                    unbilled_count=unbilled,
                    unbilled_percent=unbilled_percent,
                )
            )
        items.sort(key=lambda x: (x.role, x.department_type))

        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        return RoleWiseBilledPage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=paged,
        )

    async def get_experience(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> ExperiencePage:
        users = await self.repo.list_users_for_workforce_overview(search=search, statuses=self._ACTIVE_STATUSES)
        yoe_map = await self.repo.list_profile_yoe([int(u.id) for u in users])
        today = date.today()

        items: list[ExperienceItem] = []
        for user in users:
            doj = user.doj
            webknot_months = _months_between(doj, today) if doj else 0
            webknot_text = _format_year_month(webknot_months)

            previous_years = max(0, int(yoe_map.get(int(user.id), 0)))
            total_months = webknot_months + (previous_years * 12)
            total_text = _format_year_month(total_months)

            items.append(
                ExperienceItem(
                    emp_id=user.emp_id,
                    email=user.email,
                    name=user.name,
                    department=user.department,
                    role=user.role,
                    department_type=_normalize_department_type(user.delivery_status),
                    webknot_experience=webknot_text,
                    total_experience=total_text,
                )
            )
        items.sort(key=lambda x: (x.name, x.email))

        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        return ExperiencePage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=paged,
        )

    async def get_utilization_by_department(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        as_of: date | None,
    ) -> DepartmentUtilizationPage:
        users = await self.repo.list_users_for_workforce_overview(search=search, statuses=self._ACTIVE_STATUSES)
        as_of_date = as_of or date.today()
        user_ids = [int(u.id) for u in users]
        allocations = await self.repo.list_active_allocations_for_users(user_ids=user_ids, as_of=as_of_date)
        users_by_id = {int(u.id): u for u in users}

        per_user = defaultdict(lambda: {"billed": 0.0, "buffer": 0.0, "investment": 0.0, "talent": 0.0, "total": 0.0})
        for user_id, allocated_hours, billing_status, project_code, _ in allocations:
            uid = int(user_id)
            if uid not in users_by_id:
                continue
            share = max(0.0, min(float(allocated_hours or 0), self._MAX_DAILY_HOURS)) / self._MAX_DAILY_HOURS
            if share <= 0:
                continue
            token = (billing_status or "").strip().upper().replace("-", "_").replace(" ", "_")
            per_user[uid]["total"] += share
            if is_talent_pool_billing(billing_status):
                per_user[uid]["talent"] += share
            elif token == "BILLED":
                per_user[uid]["billed"] += share
            elif token == "BUFFER":
                per_user[uid]["buffer"] += share
            elif token == "INVESTMENT":
                per_user[uid]["investment"] += share

        grouped = defaultdict(lambda: {"head_count": 0, "actual_billed": 0.0, "buffer": 0.0, "investment": 0.0, "talent_pool": 0.0})
        for user in users:
            uid = int(user.id)
            department = (user.department or "UNKNOWN").strip() or "UNKNOWN"
            agg = per_user.get(uid, {"billed": 0.0, "buffer": 0.0, "investment": 0.0, "talent": 0.0, "total": 0.0})
            billed = float(agg["billed"])
            buffer = float(agg["buffer"])
            investment = float(agg["investment"])
            talent = float(agg["talent"])
            total = float(agg["total"])
            if total > 1.0:
                scale = 1.0 / total
                billed *= scale
                buffer *= scale
                investment *= scale
                talent *= scale
            grouped[department]["head_count"] += 1
            grouped[department]["actual_billed"] += billed
            grouped[department]["buffer"] += buffer
            grouped[department]["investment"] += investment
            grouped[department]["talent_pool"] += talent

        items: list[DepartmentUtilizationItem] = []
        for department, agg in grouped.items():
            head_count = int(agg["head_count"])
            billed = round(float(agg["actual_billed"]), 2)
            buffer = round(float(agg["buffer"]), 2)
            investment = round(float(agg["investment"]), 2)
            talent_pool = round(float(agg["talent_pool"]), 2)
            utilization_percent = round((billed * 100.0 / head_count), 2) if head_count else 0.0
            items.append(
                DepartmentUtilizationItem(
                    department=department,
                    head_count=head_count,
                    actual_billed=billed,
                    utilization_percent=utilization_percent,
                    buffer=buffer,
                    investment=investment,
                    talent_pool=talent_pool,
                )
            )
        items.sort(key=lambda x: x.department)

        total_head_count = sum(item.head_count for item in items)
        total_billed = round(sum(item.actual_billed for item in items), 2)
        total_buffer = round(sum(item.buffer for item in items), 2)
        total_investment = round(sum(item.investment for item in items), 2)
        total_talent = round(sum(item.talent_pool for item in items), 2)
        total_utilization = round((total_billed * 100.0 / total_head_count), 2) if total_head_count else 0.0
        total_row = DepartmentUtilizationItem(
            department="Total",
            head_count=total_head_count,
            actual_billed=total_billed,
            utilization_percent=total_utilization,
            buffer=total_buffer,
            investment=total_investment,
            talent_pool=total_talent,
        )

        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        data = [*paged, total_row]
        return DepartmentUtilizationPage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=data,
        )

    async def get_bench_aging(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        as_of: date | None,
    ) -> BenchAgingPage:
        users = await self.repo.list_users_for_workforce_overview(search=search, statuses=self._ACTIVE_STATUSES)
        as_of_date = as_of or date.today()
        user_ids = [int(u.id) for u in users]
        allocations = await self.repo.list_active_allocations_for_users(user_ids=user_ids, as_of=as_of_date)
        users_by_id = {int(u.id): u for u in users}

        per_user = defaultdict(lambda: {"bench_share": 0.0, "non_bench_share": 0.0, "bench_start_dates": []})
        for user_id, allocated_hours, _billing_status, project_code, start_date in allocations:
            uid = int(user_id)
            if uid not in users_by_id:
                continue
            share = max(0.0, min(float(allocated_hours or 0), self._MAX_DAILY_HOURS)) / self._MAX_DAILY_HOURS
            if share <= 0:
                continue
            code = (project_code or "").strip().upper()
            if code == BENCH_PROJECT_CODE:
                per_user[uid]["bench_share"] += share
                per_user[uid]["bench_start_dates"].append(start_date)
            else:
                per_user[uid]["non_bench_share"] += share

        items: list[BenchAgingItem] = []
        for uid, user in users_by_id.items():
            agg = per_user.get(uid, {"bench_share": 0.0, "non_bench_share": 0.0, "bench_start_dates": []})
            bench_share = float(agg["bench_share"])
            non_bench_share = float(agg["non_bench_share"])
            if bench_share <= 0 or non_bench_share > 0:
                continue
            bench_dates: list[date] = list(agg["bench_start_dates"])
            bench_days = (as_of_date - min(bench_dates)).days if bench_dates else None
            items.append(
                BenchAgingItem(
                    emp_id=user.emp_id,
                    email=user.email,
                    name=user.name,
                    department=user.department,
                    bench_days=bench_days,
                )
            )
        items.sort(key=lambda x: (x.department or "", x.name, x.email))

        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        return BenchAgingPage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=paged,
        )

    async def get_skill_inventory(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
    ) -> SkillInventoryPage:
        rows = await self.repo.list_users_for_skill_inventory(search=search, statuses=self._ACTIVE_STATUSES)
        user_ids = [int(row[0]) for row in rows]
        cert_rows = await self.repo.list_certification_documents_by_users(user_ids=user_ids)

        certs_by_user: dict[int, list[str]] = defaultdict(list)
        for user_id, file_url in cert_rows:
            if file_url:
                certs_by_user[int(user_id)].append(file_url)

        items: list[SkillInventoryItem] = []
        for user_id, emp_id, email, name, department, role, primary_skills, secondary_skills in rows:
            primary = [skill.strip() for skill in (primary_skills or []) if isinstance(skill, str) and skill.strip()]
            secondary = _normalize_secondary_skills(secondary_skills)
            items.append(
                SkillInventoryItem(
                    emp_id=emp_id,
                    email=email,
                    name=name,
                    department=department,
                    role=role,
                    primary_skills=primary,
                    secondary_skills=secondary,
                    certifications=certs_by_user.get(int(user_id), []),
                )
            )

        items.sort(key=lambda x: (x.name, x.email))
        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        return SkillInventoryPage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=paged,
        )

    async def get_contract_distribution(
        self,
        *,
        page: int,
        size: int,
    ) -> ContractDistributionPage:
        rows = await self.repo.count_workforce_by_employment_type(statuses=self._ACTIVE_STATUSES)
        by_type = {k.upper(): v for k, v in rows}
        total = sum(by_type.values())
        items = [
            ContractDistributionItem(
                employment_type="Full-Time",
                count=int(by_type.get("FULLTIME", 0)),
                workforce_percent=round((float(by_type.get("FULLTIME", 0)) * 100.0 / total), 2) if total else 0.0,
            ),
            ContractDistributionItem(
                employment_type="Intern",
                count=int(by_type.get("INTERN", 0)),
                workforce_percent=round((float(by_type.get("INTERN", 0)) * 100.0 / total), 2) if total else 0.0,
            ),
            ContractDistributionItem(
                employment_type="Consultant",
                count=int(by_type.get("CONSULTANT", 0)),
                workforce_percent=round((float(by_type.get("CONSULTANT", 0)) * 100.0 / total), 2) if total else 0.0,
            ),
            ContractDistributionItem(
                employment_type="Total",
                count=int(total),
                workforce_percent=100.0 if total else 0.0,
            ),
        ]
        p = _page_bounds(page=page, size=size, total=len(items))
        paged = items[p.start : p.end] if p.start < p.total_element else []
        return ContractDistributionPage(
            current_page=p.current_page,
            total_page=p.total_page,
            page_size=p.page_size,
            total_element=p.total_element,
            data=paged,
        )

    @staticmethod
    def _fy_calendar_bounds(fy_start_year: int) -> tuple[date, date]:
        """India FY: 1 April fy_start_year through 31 March fy_start_year + 1."""
        return date(fy_start_year, 4, 1), date(fy_start_year + 1, 3, 31)

    @staticmethod
    def _parse_manager_user_ids(pm: str | None) -> list[int]:
        """Parse comma-separated ``users.id`` values; dedupe and sort for stable grouping."""
        if pm is None:
            return []
        out: list[int] = []
        for part in str(pm).split(","):
            p = part.strip()
            if not p:
                continue
            try:
                out.append(int(p))
            except ValueError:
                continue
        return sorted(set(out))

    async def build_attrition_fy_report(self, *, fy_start_year: int) -> AttritionFYReport:
        fy_april_start, fy_march_end = self._fy_calendar_bounds(fy_start_year)
        rows = await self.attrition_repo.list_with_users_for_date_range(
            start_inclusive=fy_april_start,
            end_inclusive=fy_march_end,
        )
        exit_count = len(rows)

        total_office_headcount = await self.attrition_repo.count_users_with_statuses(
            statuses=self._ACTIVE_STATUSES,
        )
        overall_attrition_percent = (
            round((exit_count * 100.0 / total_office_headcount), 2) if total_office_headcount else 0.0
        )

        voluntary = 0
        involuntary = 0
        role_counts: dict[str, int] = defaultdict(int)
        mgr_counts: dict[str, int] = defaultdict(int)
        skill_counts: dict[str, int] = defaultdict(int)
        regretted_exit_count = 0
        tenure_bucket_counts: dict[str, int] = defaultdict(int)
        tenure_days_list: list[int] = []

        tenure_meta = {
            "EARLY_0_30": ("Early Exit", "0 – 30 Days"),
            "SHORT_31_60": ("Short Tenure", "31 – 60 Days"),
            "MEDIUM_61_90": ("Medium Tenure", "61 – 90 Days"),
            "LONG_90_PLUS": ("Long Tenure", "90+ Days"),
            "UNKNOWN": ("Unknown", "Date of joining not set"),
        }

        for attr, user in rows:
            st = (attr.separation_type or "").strip().upper()
            if st == self._SEPARATION_VOLUNTARY:
                voluntary += 1
            elif st == self._SEPARATION_INVOLUNTARY:
                involuntary += 1

            role_key = (attr.designation or user.role or "UNKNOWN").strip() or "UNKNOWN"
            role_counts[role_key] += 1

            mgr_ids = self._parse_manager_user_ids(getattr(attr, "project_manager", None))
            if not mgr_ids:
                lbl = await self.attrition_repo.resolve_project_manager_label(
                    user_id=int(user.id),
                    last_working_day=attr.last_working_day,
                )
                mgr_ids = self._parse_manager_user_ids(lbl)
            mgr_bucket = ",".join(str(i) for i in mgr_ids) if mgr_ids else "__UNKNOWN__"
            mgr_counts[mgr_bucket] += 1

            if attr.critical_skill and str(attr.critical_skill).strip():
                sk = str(attr.critical_skill).strip()
                skill_counts[sk] += 1

            if attr.is_regretted:
                regretted_exit_count += 1

            doj = user.doj
            lwd = attr.last_working_day
            if doj is None:
                tenure_bucket_counts["UNKNOWN"] += 1
            else:
                td = (lwd - doj).days
                tenure_days_list.append(td)
                if td <= 30:
                    tenure_bucket_counts["EARLY_0_30"] += 1
                elif td <= 60:
                    tenure_bucket_counts["SHORT_31_60"] += 1
                elif td <= 90:
                    tenure_bucket_counts["MEDIUM_61_90"] += 1
                else:
                    tenure_bucket_counts["LONG_90_PLUS"] += 1

        regretted_percent_of_exits = (
            round((regretted_exit_count * 100.0 / exit_count), 2) if exit_count else 0.0
        )
        average_tenure_days = (
            round(sum(tenure_days_list) / len(tenure_days_list), 2) if tenure_days_list else None
        )

        role_rows = [
            AttritionRoleWiseItem(role_or_designation=r, exit_count=c)
            for r, c in sorted(role_counts.items(), key=lambda x: (-x[1], x[0]))
        ]

        mgr_id_union: list[int] = []
        for key in mgr_counts:
            if key == "__UNKNOWN__":
                continue
            mgr_id_union.extend(int(x) for x in key.split(",") if x.strip())
        id_to_name = await self.user_repo.map_names_by_user_ids(mgr_id_union)

        def _manager_display(bucket_key: str) -> str:
            if bucket_key == "__UNKNOWN__":
                return "Unknown"
            labels: list[str] = []
            for part in bucket_key.split(","):
                if not part.strip():
                    continue
                uid = int(part)
                labels.append(id_to_name.get(uid) or f"User {uid}")
            return ", ".join(labels) if labels else "Unknown"

        manager_wise = [
            AttritionManagerWiseItem(reporting_manager=_manager_display(k), exit_count=c)
            for k, c in sorted(mgr_counts.items(), key=lambda x: (-x[1], x[0]))
        ]
        critical_skill_wise = [
            AttritionCriticalSkillItem(critical_skill=s, exit_count=c)
            for s, c in sorted(skill_counts.items(), key=lambda x: (-x[1], x[0]))
        ]

        bucket_order = ["EARLY_0_30", "SHORT_31_60", "MEDIUM_61_90", "LONG_90_PLUS", "UNKNOWN"]
        tenure_bucket_rows = [
            AttritionTenureBucketItem(
                tenure_bucket=tenure_meta[k][0],
                range_days=tenure_meta[k][1],
                number_of_employees=int(tenure_bucket_counts.get(k, 0)),
            )
            for k in bucket_order
        ]

        return AttritionFYReport(
            fy_period=AttritionFYPeriod(
                fy_start_year=fy_start_year,
                fy_april_start=fy_april_start,
                fy_march_end=fy_march_end,
            ),
            overall_attrition_percent=AttritionOverallPercentTable(
                fy_start_year=fy_start_year,
                fy_april_start=fy_april_start,
                fy_march_end=fy_march_end,
                number_of_exits=exit_count,
                attrition_percent=overall_attrition_percent,
            ),
            voluntary_vs_involuntary=AttritionVoluntaryInvoluntaryTable(
                voluntary_count=voluntary,
                involuntary_count=involuntary,
                total_count=voluntary + involuntary,
            ),
            role_wise_attrition=AttritionRoleWiseTable(rows=role_rows),
            manager_wise_attrition=AttritionManagerWiseTable(rows=manager_wise),
            critical_skill_attrition=AttritionCriticalSkillTable(rows=critical_skill_wise),
            regretted_attrition=AttritionRegrettedTable(
                total_regretted_exits=regretted_exit_count,
                percent_of_total_attrition=regretted_percent_of_exits,
            ),
            average_tenure=AttritionAverageTenureTable(
                buckets=tenure_bucket_rows,
                average_tenure_days=average_tenure_days,
                tenure_unknown_employees=int(tenure_bucket_counts.get("UNKNOWN", 0)),
            ),
        )

    async def get_attrition_overall_percent(self, *, fy_start_year: int) -> AttritionOverallPercentTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.overall_attrition_percent

    async def get_attrition_voluntary_involuntary(self, *, fy_start_year: int) -> AttritionVoluntaryInvoluntaryTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.voluntary_vs_involuntary

    async def get_attrition_role_wise(self, *, fy_start_year: int) -> AttritionRoleWiseTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.role_wise_attrition

    async def get_attrition_manager_wise(self, *, fy_start_year: int) -> AttritionManagerWiseTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.manager_wise_attrition

    async def get_attrition_critical_skill(self, *, fy_start_year: int) -> AttritionCriticalSkillTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.critical_skill_attrition

    async def get_attrition_regretted(self, *, fy_start_year: int) -> AttritionRegrettedTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.regretted_attrition

    async def get_attrition_average_tenure(self, *, fy_start_year: int) -> AttritionAverageTenureTable:
        report = await self.build_attrition_fy_report(fy_start_year=fy_start_year)
        return report.average_tenure

    async def get_attrition_record(self, *, emp_id: str) -> AttritionRecordResponse:
        user = await self.attrition_repo.get_user_by_emp_id(emp_id=emp_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        row = await self.attrition_repo.get_by_user_id(user_id=int(user.id))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attrition record not found")
        return AttritionRecordResponse(
            emp_id=user.emp_id,
            employee_name=row.employee_name,
            separation_type=row.separation_type,
            reason=row.reason,
            critical_skill=row.critical_skill,
            is_regretted=bool(row.is_regretted),
            resignation_date=row.resignation_date,
            last_working_day=row.last_working_day,
            notice_period_days=row.notice_period_days,
            designation=row.designation,
            band_name=row.band_name,
            band_role=row.band_role,
            project_manager=row.project_manager,
        )

    async def upsert_attrition(self, *, actor_email: str, emp_id: str, payload: AttritionUpsertRequest) -> AttritionRecordResponse:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actor not found")
        user = await self.attrition_repo.get_user_by_emp_id(emp_id=emp_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

        sep = payload.separation_type.strip().upper()
        if sep not in (self._SEPARATION_VOLUNTARY, self._SEPARATION_INVOLUNTARY):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="separation_type must be VOLUNTARY or INVOLUNTARY",
            )

        band_name, designation, band_role = await self.attrition_repo.build_band_snapshots(user=user)
        pm = await self.attrition_repo.resolve_project_manager_label(
            user_id=int(user.id),
            last_working_day=payload.last_working_day,
        )

        db_payload = {
            "employee_name": user.name,
            "separation_type": sep,
            "reason": payload.reason,
            "critical_skill": payload.critical_skill,
            "is_regretted": payload.is_regretted,
            "resignation_date": payload.resignation_date,
            "last_working_day": payload.last_working_day,
            "notice_period_days": payload.notice_period_days,
            "designation": designation,
            "band_name": band_name,
            "band_role": band_role,
            "project_manager": pm,
        }
        await self.attrition_repo.upsert_for_user(
            user_id=int(user.id),
            actor_id=int(actor.id),
            payload=db_payload,
        )
        return await self.get_attrition_record(emp_id=emp_id)

