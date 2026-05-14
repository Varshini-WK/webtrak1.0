from datetime import date

from app.services.leave_reporting_service import LeaveReportingService


def test_count_weekdays_full_week() -> None:
    # 2026-05-04 is Monday through 2026-05-10 Sunday -> 5 weekdays
    assert LeaveReportingService._count_weekdays(date(2026, 5, 4), date(2026, 5, 10)) == 5


def test_count_weekdays_single_saturday() -> None:
    assert LeaveReportingService._count_weekdays(date(2026, 5, 9), date(2026, 5, 9)) == 0


def test_count_weekdays_inclusive_same() -> None:
    assert LeaveReportingService._count_weekdays(date(2026, 5, 5), date(2026, 5, 5)) == 1  # Tuesday
