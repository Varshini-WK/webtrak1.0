from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.scheduled_jobs_service import ScheduledJobsService

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler


def start_scheduler(*, db, timezone: str = "UTC") -> AsyncIOScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    service = ScheduledJobsService(db)
    scheduler = AsyncIOScheduler(timezone=timezone)

    # Legacy: @Scheduled(cron = "0 0 0 */3 * ?")
    scheduler.add_job(
        service.send_timelog_defaults_notifications,
        trigger=CronTrigger(second=0, minute=0, hour=0, day="*/3"),
        id="timelog_defaults_every_3_days",
        replace_existing=True,
    )

    # Legacy: @Scheduled(cron = "0 0 0 * * *")
    scheduler.add_job(
        service.send_internship_completion_notifications,
        trigger=CronTrigger(second=0, minute=0, hour=0, day="*", month="*", day_of_week="*"),
        id="internship_completion_daily",
        replace_existing=True,
    )

    # Legacy: @Scheduled(cron = "12 0 0 * * *")
    scheduler.add_job(
        service.deallocate_expired_allocations,
        trigger=CronTrigger(second=12, minute=0, hour=0, day="*", month="*", day_of_week="*"),
        id="deallocate_daily",
        replace_existing=True,
    )

    # Legacy: @Scheduled(cron = "0 0 0 1 * *")
    scheduler.add_job(
        service.add_monthly_leaves_and_carry_forward,
        trigger=CronTrigger(second=0, minute=0, hour=0, day=1),
        id="monthly_leave_rollup",
        replace_existing=True,
    )

    # Legacy: @Scheduled(cron = "0 45 11 * * *")
    scheduler.add_job(
        service.remind_leave_approval,
        trigger=CronTrigger(second=0, minute=45, hour=11, day="*", month="*", day_of_week="*"),
        id="leave_reminder_1145",
        replace_existing=True,
    )

    # Legacy: @Scheduled(cron = "0 30 11 * * *")
    scheduler.add_job(
        service.remind_leave_approval,
        trigger=CronTrigger(second=0, minute=30, hour=11, day="*", month="*", day_of_week="*"),
        id="leave_reminder_1130",
        replace_existing=True,
    )

    # Legacy: @Scheduled(cron = "0 0 12 * * *")
    scheduler.add_job(
        service.auto_approve_leave_if_manager_not_approved,
        trigger=CronTrigger(second=0, minute=0, hour=12, day="*", month="*", day_of_week="*"),
        id="leave_auto_approve_daily",
        replace_existing=True,
    )

    # Legacy notification cleanup: @Scheduled(fixedRate = 30 * 60 * 1000)
    scheduler.add_job(
        service.delete_read_notifications,
        trigger=IntervalTrigger(minutes=30),
        id="notification_cleanup_30m",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with %s jobs", len(scheduler.get_jobs()))
    _scheduler = scheduler
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None

