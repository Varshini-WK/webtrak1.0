from datetime import date

from app.schemas.leave_reporting import AttendanceLeaveReportPage, LeaveSummaryPage
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

    async def fetch_attendance_leave_report(
        self,
        *,
        from_date: date,
        to_date: date,
        search: str | None,
        user_type: str | None,
        band: str | None,
        page: int,
        size: int,
    ) -> AttendanceLeaveReportPage:
        return await self.service.fetch_attendance_leave_report(
            from_date=from_date,
            to_date=to_date,
            search=search,
            user_type=user_type,
            band=band,
            page=page,
            size=size,
        )

