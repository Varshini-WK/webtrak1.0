from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
import logging
from time import perf_counter

from sqlalchemy import and_, func, or_, select

from app.models.leave_mapping import LeaveMapping
from app.domain.notification_types import NotificationType
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.models.user_request_tracking import UserRequestTracking
from app.models.allocation import Allocation
from app.models.project import Project
from app.models.timelog import TimeLog
from app.repositories.allocation_repository import AllocationRepository
from app.repositories.leave_repository import LeaveRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.timelog_repository import TimeLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_request_repository import UserRequestRepository
from app.repositories.user_request_tracking_repository import UserRequestTrackingRepository
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.domain.email_templates import LEAVE_APPROVAL_REMAINDER, NO_TIME_LOGS
from app.domain.message_constants import (
    LEAVE_APPROVAL_REMAINDER_SUBJECT,
    NO_TIME_LOGS_SUBJECT,
)

logger = logging.getLogger(__name__)


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def _last_working_days(interval: int) -> list[date]:
    days: list[date] = []
    current = date.today() - timedelta(days=1)
    while len(days) < interval:
        if current.weekday() < 5:
            days.append(current)
        current -= timedelta(days=1)
    return days


@dataclass
class JobRunResult:
    name: str
    success: bool
    count: int
    duration_ms: int
    error: str | None = None


class ScheduledJobsService:
    def __init__(self, db) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.alloc_repo = AllocationRepository(db)
        self.request_repo = UserRequestRepository(db)
        self.tracking_repo = UserRequestTrackingRepository(db)
        self.leave_repo = LeaveRepository(db)
        self.notification_repo = NotificationRepository(db)
        self.notification_service = NotificationService(db)
        self.timelog_repo = TimeLogRepository(db)
        self.email_service = EmailService()

    async def send_timelog_defaults_notifications(self) -> int:
        interval = 3
        days = _last_working_days(interval)
        candidate_user_ids = await self.alloc_repo.list_user_ids_with_non_bench_on_dates(days)
        if not candidate_user_ids:
            return 0

        sent = 0
        for user_id in candidate_user_ids:
            user = await self.user_repo.get_by_id(user_id)
            if user is None:
                continue
            logged_hours = await self.timelog_repo.sum_hours_for_user_on_dates(user_id, days)
            expected = float(len(days) * 8)
            if logged_hours >= expected:
                continue
            await self.notification_service.send_notification(
                receiver_id=user.id,
                sender_id=None,
                notification_type=NotificationType.NO_TIME_LOGS,
                title="Timesheet Reminder",
                message=f"You have logged {logged_hours:.1f}h across the last {len(days)} working days.",
            )
            sent += 1

        # Java-parity: also send per-user-per-project emails with cc=project manager.
        # We keep the existing in-app notification behavior unchanged.
        try:
            await self._send_no_time_logs_emails(days=days, interval=interval)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send time-log reminder emails")

        return sent

    async def _send_no_time_logs_emails(self, *, days: list[date], interval: int) -> None:
        if not days:
            return

        today = date.today()
        sent = 0

        # Select active IN_HOUSE allocations and compute logged hours per user+project for those days.
        # Java query also filters allocations by end_date (null or >= CURRENT_DATE).
        async with self.db.session() as session:
            alloc_stmt = (
                select(
                    Allocation.user_id,
                    Allocation.project_id,
                    Allocation.allocated_hours,
                    User.email,
                    User.name,
                    Project.project_name,
                )
                .select_from(Allocation)
                .join(User, Allocation.user_id == User.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(
                    Project.project_type == "IN_HOUSE",
                    Allocation.is_active.is_(True),
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= today),
                )
            )
            alloc_rows = list((await session.execute(alloc_stmt)).all())

            for row in alloc_rows:
                user_id = int(row[0])
                project_id = int(row[1])
                allocated_hours = float(row[2] or 0.0)
                user_email = str(row[3])
                user_name = str(row[4])
                project_name = str(row[5])

                sum_stmt = (
                    select(func.coalesce(func.sum(TimeLog.logged_hours), 0.0))
                    .where(
                        TimeLog.user_id == user_id,
                        TimeLog.project_id == project_id,
                        TimeLog.log_date.in_(days),
                    )
                )
                logged_hours = float((await session.scalar(sum_stmt)) or 0.0)
                if logged_hours >= allocated_hours * float(interval):
                    continue

                # Manager emails for this project (may be multiple).
                mgr_stmt = (
                    select(User.email)
                    .select_from(UserRole)
                    .join(Role, UserRole.role_id == Role.id)
                    .join(User, UserRole.user_id == User.id)
                    .where(
                        UserRole.project_id == project_id,
                        Role.name.in_(["ROLE_MANAGER", "MANAGER"]),
                    )
                    .distinct()
                )
                manager_emails = [r for r in (await session.scalars(mgr_stmt)).all() if r]
                body = NO_TIME_LOGS % (user_name, project_name, interval, logged_hours)
                for manager_email in manager_emails:
                    await self.email_service.send_email(
                        to=user_email,
                        subject=NO_TIME_LOGS_SUBJECT,
                        body=body,
                        cc=manager_email,
                        is_html=True,
                    )
                    sent += 1

        logger.info("Sent %s NO_TIME_LOGS emails", sent)

    async def send_internship_completion_notifications(self) -> int:
        today = date.today()
        interns = await self.user_repo.list_interns_with_doi_and_duration()
        hr_users = await self.user_repo.list_users_by_role_names(["ROLE_HR", "HR"])
        if not interns or not hr_users:
            return 0

        day_start = datetime.combine(today, time.min, tzinfo=UTC).replace(tzinfo=None)
        day_end = datetime.combine(today, time.max, tzinfo=UTC).replace(tzinfo=None)
        sent = 0
        for intern in interns:
            if not intern.doi or not intern.internship_duration:
                continue
            completion_day = _add_months(intern.doi, int(intern.internship_duration))
            if completion_day != today:
                continue
            already = await self.notification_repo.exists_for_sender_type_between(
                sender_id=intern.id,
                notification_type="INTERNSHIP_ABOUT_TO_COMPLETE",
                start_at=day_start,
                end_at=day_end,
            )
            if already:
                continue
            for hr in hr_users:
                already_for_receiver = await self.notification_repo.exists_for_receiver_sender_type_between(
                    receiver_id=hr.id,
                    sender_id=intern.id,
                    notification_type=NotificationType.INTERNSHIP_ABOUT_TO_COMPLETE.value,
                    start_at=day_start,
                    end_at=day_end,
                )
                if already_for_receiver:
                    continue
                await self.notification_service.send_notification(
                    receiver_id=hr.id,
                    sender_id=intern.id,
                    notification_type=NotificationType.INTERNSHIP_ABOUT_TO_COMPLETE,
                    title="Internship Completing Today",
                    message=f"Internship of {intern.name} ({intern.email}) completes today.",
                )
                sent += 1
        return sent

    async def deallocate_expired_allocations(self) -> int:
        today = date.today()
        rows = await self.alloc_repo.list_active_expired(today)
        if not rows:
            return 0
        user_project_pairs = [(int(row.user_id), int(row.project_id)) for row in rows]
        async with self.db.tx() as tx:
            for row in rows:
                row.is_active = False
                tx.add(row)
            await tx.flush()
        for user_id, project_id in user_project_pairs:
            await self.notification_service.send_notification(
                receiver_id=user_id,
                sender_id=None,
                notification_type=NotificationType.PROJECT_DEALLOCATION,
                title="Project Deallocation",
                message=f"Your allocation for project id {project_id} has ended.",
            )
        return len(rows)

    async def add_monthly_leaves_and_carry_forward(self) -> int:
        current_month = date.today().month
        current_year = date.today().year
        last_year = current_year - 1
        last_month = 12 if current_month == 1 else current_month - 1
        prev_year_for_last_month = current_year - 1 if current_month == 1 else current_year

        users = await self.user_repo.list_all_users()
        touched = 0
        async with self.db.tx() as tx:
            for user in users:
                current = await self.leave_repo.get_mapping(user.id, current_year, current_month, client=tx)
                last_m = await self.leave_repo.get_mapping(user.id, prev_year_for_last_month, last_month, client=tx)
                last_y_dec = await self.leave_repo.get_mapping(user.id, last_year, 12, client=tx)

                if current is None:
                    current = LeaveMapping(
                        user_id=user.id,
                        year=current_year,
                        month=current_month,
                        primary_leave=0.0,
                        secondary_leave=0.0,
                        carry_forward=0.0,
                    )
                    tx.add(current)
                    await tx.flush()

                if str(user.userType).upper() == "INTERN":
                    current.primary_leave = 0.0
                    current.secondary_leave = 0.0
                    current.carry_forward = 0.0
                    touched += 1
                    continue

                if current_month == 1 and last_y_dec is not None:
                    carry = float(last_y_dec.primary_leave or 0.0)
                    current.secondary_leave = carry
                    current.carry_forward = carry

                prev_primary = float(last_m.primary_leave or 0.0) if last_m else 0.0
                prev_secondary = float(last_m.secondary_leave or 0.0) if last_m else 0.0
                prev_carry = float(last_m.carry_forward or 0.0) if last_m else 0.0

                if current_month <= 7:
                    if current_month == 1:
                        current.primary_leave = 1.5
                    else:
                        current.primary_leave = 1.5 if prev_primary < 0 else prev_primary + 1.5
                    current.secondary_leave = 0.0 if prev_secondary < 0 else prev_secondary
                    current.carry_forward = prev_carry
                else:
                    current.secondary_leave = 1.5 if prev_secondary < 0 else prev_secondary + 1.5
                    current.primary_leave = 0.0 if prev_primary < 0 else prev_primary
                    current.carry_forward = prev_carry

                touched += 1
            await tx.flush()
        return touched

    async def _manager_actioner_ids(self, user_request_id: int, client) -> list[int]:
        rows = (
            await client.execute(
                select(UserRequestTracking.actioner_id)
                .distinct()
                .join(UserRole, UserRole.user_id == UserRequestTracking.actioner_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRequestTracking.user_request_id == user_request_id,
                    UserRequestTracking.action == "INITIATED",
                    Role.name.in_(["ROLE_MANAGER", "MANAGER"]),
                )
            )
        ).all()
        return sorted({int(x[0]) for x in rows})

    async def remind_leave_approval(self) -> int:
        today = date.today()
        requests = await self.request_repo.list_pending_for_exact_day(day=today, request_types=["LEAVE", "WFH"])
        sent = 0
        async with self.db.tx() as tx:
            for req in requests:
                manager_ids = await self._manager_actioner_ids(req.id, tx)
                if not manager_ids:
                    continue
                for manager_id in manager_ids:
                    already_sent = await self.notification_repo.exists_for_receiver_sender_type_between(
                        receiver_id=manager_id,
                        sender_id=req.user_id,
                        notification_type=NotificationType.LEAVE_APPROVAL_REMINDER.value,
                        start_at=datetime.combine(today, time.min),
                        end_at=datetime.combine(today, time.max),
                    )
                    if already_sent:
                        continue
                    has_decision = await self.tracking_repo.has_action_for_request_and_actioners(
                        user_request_id=req.id,
                        actions=["APPROVED", "REJECTED", "APPROVED_BY_DEFAULT"],
                        actioner_ids=[manager_id],
                    )
                    if has_decision:
                        continue
                    await self.notification_service.send_notification(
                        receiver_id=manager_id,
                        sender_id=req.user_id,
                        notification_type=NotificationType.LEAVE_APPROVAL_REMINDER,
                        title="Pending Leave/WFH Approval",
                        message=f"Approval pending for request #{req.id}.",
                        client=tx,
                    )

                    # Java-parity: send manager email, cc requestor email.
                    try:
                        manager = await self.user_repo.get_by_id(manager_id)
                        if manager:
                            requestor_email = req.user.email
                            requestor_name = req.user.name
                            subject = LEAVE_APPROVAL_REMAINDER_SUBJECT % requestor_name
                            body = LEAVE_APPROVAL_REMAINDER % ("Manager", requestor_name)
                            await self.email_service.send_email(
                                to=manager.email,
                                subject=subject,
                                body=body,
                                cc=requestor_email,
                                is_html=True,
                            )
                    except Exception:  # noqa: BLE001
                        logger.exception("Failed to send leave approval reminder email")

                    sent += 1
            await tx.flush()
        return sent

    async def auto_approve_leave_if_manager_not_approved(self) -> int:
        today = date.today()
        requests = await self.request_repo.list_pending_for_exact_day(day=today, request_types=["LEAVE", "WFH"])
        created = 0
        async with self.db.tx() as tx:
            for req in requests:
                manager_ids = await self._manager_actioner_ids(req.id, tx)
                if not manager_ids:
                    continue
                any_approved = await self.tracking_repo.has_action_for_request_and_actioners(
                    user_request_id=req.id,
                    actions=["APPROVED", "APPROVED_BY_DEFAULT"],
                    actioner_ids=manager_ids,
                )
                if any_approved:
                    continue
                auto_approved = False
                for manager_id in manager_ids:
                    await self.tracking_repo.create(
                        {
                            "action": "APPROVED_BY_DEFAULT",
                            "user_request_id": req.id,
                            "actioner_id": manager_id,
                            "project_id": None,
                            "message": "Auto-approved by scheduled job",
                        },
                        client=tx,
                    )
                    created += 1
                    auto_approved = True
                if auto_approved:
                    await self.notification_service.send_notification(
                        receiver_id=req.user_id,
                        sender_id=None,
                        notification_type=NotificationType.LEAVE_AUTO_APPROVED,
                        title="Leave Auto-Approved",
                        message=f"Request #{req.id} was auto-approved by default policy.",
                        client=tx,
                    )
            await tx.flush()
        return created

    async def delete_read_notifications(self) -> int:
        deleted = await self.notification_repo.delete_read_notifications()
        logger.info("Deleted read notifications count=%s", deleted)
        return deleted

    async def run_all_jobs(self) -> dict:
        jobs: list[tuple[str, callable]] = [
            ("send_timelog_defaults_notifications", self.send_timelog_defaults_notifications),
            ("send_internship_completion_notifications", self.send_internship_completion_notifications),
            ("deallocate_expired_allocations", self.deallocate_expired_allocations),
            ("add_monthly_leaves_and_carry_forward", self.add_monthly_leaves_and_carry_forward),
            ("remind_leave_approval", self.remind_leave_approval),
            ("auto_approve_leave_if_manager_not_approved", self.auto_approve_leave_if_manager_not_approved),
            ("delete_read_notifications", self.delete_read_notifications),
        ]
        results: list[JobRunResult] = []
        for name, fn in jobs:
            start = perf_counter()
            try:
                count = int(await fn())
                duration_ms = int((perf_counter() - start) * 1000)
                results.append(JobRunResult(name=name, success=True, count=count, duration_ms=duration_ms))
            except Exception as exc:  # noqa: BLE001
                duration_ms = int((perf_counter() - start) * 1000)
                results.append(
                    JobRunResult(
                        name=name,
                        success=False,
                        count=0,
                        duration_ms=duration_ms,
                        error=str(exc),
                    )
                )
        return {
            "total_jobs": len(results),
            "success_jobs": len([r for r in results if r.success]),
            "failed_jobs": len([r for r in results if not r.success]),
            "results": [r.__dict__ for r in results],
        }
