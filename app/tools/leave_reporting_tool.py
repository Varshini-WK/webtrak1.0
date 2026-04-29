from app.schemas.leave_reporting import LeaveSummaryPage
from app.services.leave_reporting_service import LeaveReportingService


class LeaveReportingTool:
    def __init__(self, db) -> None:
        self.service = LeaveReportingService(db)

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
        return await self.service.fetch_leave_summary(
            page=page,
            size=size,
            search=search,
            user_type=user_type,
            band=band,
            year=year,
            month=month,
        )

