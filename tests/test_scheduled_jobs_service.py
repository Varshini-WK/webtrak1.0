import asyncio
from unittest.mock import MagicMock

from app.services.scheduled_jobs_service import ScheduledJobsService


def test_run_all_jobs_summary_handles_success_and_failure() -> None:
    service = ScheduledJobsService(MagicMock())

    async def ok() -> int:
        return 3

    async def fail() -> int:
        raise RuntimeError("boom")

    service.send_timelog_defaults_notifications = ok  # type: ignore[method-assign]
    service.send_internship_completion_notifications = ok  # type: ignore[method-assign]
    service.deallocate_expired_allocations = ok  # type: ignore[method-assign]
    service.add_monthly_leaves_and_carry_forward = fail  # type: ignore[method-assign]
    service.remind_leave_approval = ok  # type: ignore[method-assign]
    service.auto_approve_leave_if_manager_not_approved = ok  # type: ignore[method-assign]
    service.delete_read_notifications = ok  # type: ignore[method-assign]

    summary = asyncio.run(service.run_all_jobs())
    assert summary["total_jobs"] == 7
    assert summary["success_jobs"] == 6
    assert summary["failed_jobs"] == 1
    failed = [r for r in summary["results"] if not r["success"]]
    assert len(failed) == 1
    assert failed[0]["name"] == "add_monthly_leaves_and_carry_forward"
    assert "boom" in failed[0]["error"]

