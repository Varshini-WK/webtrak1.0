from __future__ import annotations

from collections import defaultdict
from datetime import date

from fastapi import HTTPException, status

from app.repositories.leave_repository import LeaveRepository
from app.repositories.leave_transaction_repository import LeaveTransactionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.leave_reporting import LeaveDetailsResponse, LeaveSummaryItem, LeaveSummaryPage


class LeaveReportingService:
    def __init__(self, db) -> None:
        self.user_repo = UserRepository(db)
        self.leave_repo = LeaveRepository(db)
        self.leave_tx_repo = LeaveTransactionRepository(db)

    async def _get_leave_details_for_lop(self, *, user_id: int, year: int, month: int, lop: float) -> list[LeaveDetailsResponse]:
        if lop <= 0:
            return []
        txns = await self.leave_tx_repo.list_for_user_month(user_id, year, month)
        deducts = [t for t in txns if str(t.transaction_type).upper() == "DEDUCT"]
        deducts.sort(key=lambda x: (x.for_date, x.id))
        grouped: dict[int, list] = defaultdict(list)
        remaining = float(lop)
        for txn in deducts:
            if remaining <= 0:
                break
            grouped[int(txn.user_request_id or 0)].append(txn)
            remaining -= float(txn.value or 0.0)

        details: list[LeaveDetailsResponse] = []
        for request_id, entries in grouped.items():
            if request_id == 0:
                for entry in entries:
                    value = float(entry.value or 0.0)
                    details.append(
                        LeaveDetailsResponse(
                            from_date=entry.for_date,
                            to_date=entry.for_date,
                            is_half_day=value == 0.5,
                            leave_count=0.5 if value == 0.5 else 1.0,
                        )
                    )
                continue

            entries.sort(key=lambda x: x.for_date)
            if len(entries) == 1:
                value = float(entries[0].value or 0.0)
                details.append(
                    LeaveDetailsResponse(
                        from_date=entries[0].for_date,
                        to_date=entries[0].for_date,
                        is_half_day=value == 0.5,
                        leave_count=0.5 if value == 0.5 else 1.0,
                    )
                )
            else:
                details.append(
                    LeaveDetailsResponse(
                        from_date=entries[0].for_date,
                        to_date=entries[-1].for_date,
                        is_half_day=False,
                        leave_count=float(len(entries)),
                    )
                )
        details.sort(key=lambda x: (x.from_date, x.to_date))
        return details

    async def fetch_leave_summary(
        self,
        *,
        page: int,
        size: int,
        search: str | None,
        user_type: str | None,
        band: str | None,
        year: int | None,
        month: int | None,
    ) -> LeaveSummaryPage:
        today = date.today()
        target_year = int(year or today.year)
        target_month = int(month or today.month)
        if target_month < 1 or target_month > 12:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month")
        if target_year == today.year and target_month > today.month:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid month - Future months not allowed")

        users = await self.user_repo.list_users_with_filters(
            search=search,
            band=band,
            user_type=user_type,
            statuses=["ACTIVE", "ONBOARDING", "INVITED"],
        )
        if not users:
            return LeaveSummaryPage(current_page=page, total_page=0, page_size=size, total_element=0, data=[])

        items: list[LeaveSummaryItem] = []
        for user in users:
            mapping = await self.leave_repo.get_mapping(user.id, target_year, target_month)
            txns = await self.leave_tx_repo.list_for_user_month(user.id, target_year, target_month)
            leaves_taken = float(sum(float(t.value or 0.0) for t in txns if str(t.transaction_type).upper() == "DEDUCT"))
            lop = 0.0
            if mapping is not None:
                primary = float(mapping.primary_leave or 0.0)
                secondary = float(mapping.secondary_leave or 0.0)
                total = primary + secondary
                if total < 0:
                    lop = abs(total)

            if lop <= 0:
                continue
            details = await self._get_leave_details_for_lop(user_id=user.id, year=target_year, month=target_month, lop=lop)
            items.append(
                LeaveSummaryItem(
                    name=user.name,
                    email=user.email,
                    emp_id=user.emp_id,
                    role="",
                    type=user.user_type,
                    band=user.band.name if getattr(user, "band", None) else "",
                    leaves=leaves_taken,
                    lop=lop,
                    leave_details=details,
                )
            )

        total = len(items)
        start = page * size
        end = start + size
        paged = items[start:end] if start < total else []
        total_pages = 0 if total == 0 else (total + size - 1) // size
        return LeaveSummaryPage(
            current_page=page,
            total_page=total_pages,
            page_size=size,
            total_element=total,
            data=paged,
        )

