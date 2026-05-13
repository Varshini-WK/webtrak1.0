from __future__ import annotations

from datetime import date, datetime, timedelta
import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select

from app.domain.allocation_rules import BENCH_EQUIVALENT_PROJECT_CODES
from app.models.allocation import Allocation
from app.models.leave_mapping import LeaveMapping
from app.models.project import Project
from app.models.role import Role
from app.models.user import User
from app.models.user_request_tracking import UserRequestTracking
from app.models.user_role import UserRole
from app.domain.notification_types import NotificationType
from app.repositories.leave_transaction_repository import LeaveTransactionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_request_repository import UserRequestRepository
from app.repositories.user_request_tracking_repository import UserRequestTrackingRepository
from app.schemas.user_request import (
    UserRequestCreate,
    UserRequestListResponse,
    UserRequestOut,
    UserRequestStatusUpdate,
    UserRequestUpdate,
)
from app.services.comp_off_service import CompOffService
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.domain.email_templates import USER_REQUEST_STATUS_UPDATE, USER_REQUEST_SUBMIT


def _normalize_roles(actor_roles: set[str]) -> set[str]:
    out: set[str] = set()
    for role in actor_roles:
        role_name = role.strip().upper()
        if not role_name.startswith("ROLE_"):
            role_name = f"ROLE_{role_name}"
        out.add(role_name)
    return out


_DEDUCT_SPLIT_RE = re.compile(r"\[D:(?P<primary>-?\d+(?:\.\d+)?)P,(?P<secondary>-?\d+(?:\.\d+)?)S\]")


class UserRequestService:
    def __init__(self, db) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.request_repo = UserRequestRepository(db)
        self.tracking_repo = UserRequestTrackingRepository(db)
        self.leave_tx_repo = LeaveTransactionRepository(db)
        self.comp_off_service = CompOffService(db)
        self.notification_service = NotificationService(db)
        self.email_service = EmailService()

    @staticmethod
    def _request_created_type(request_type: str) -> NotificationType:
        req = request_type.strip().upper()
        if req == "WFH":
            return NotificationType.WFH_REQUEST
        if req == "COMP_OFF":
            return NotificationType.COMP_OFF_REQUEST
        return NotificationType.LEAVE_REQUEST

    @staticmethod
    def _request_action_type(request_type: str, action: str) -> NotificationType:
        req = request_type.strip().upper()
        act = action.strip().upper()
        if req == "WFH":
            return NotificationType.WFH_APPROVED if act == "APPROVED" else NotificationType.WFH_REJECTED
        if req == "COMP_OFF":
            return NotificationType.COMP_OFF_APPROVED if act == "APPROVED" else NotificationType.COMP_OFF_REJECTED
        return NotificationType.LEAVE_APPROVED if act == "APPROVED" else NotificationType.LEAVE_REJECTED

    async def _get_user_by_email_or_404(self, email: str) -> User:
        user = await self.user_repo.get_by_email(email.lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @staticmethod
    def _validate_request_payload(payload: UserRequestCreate | UserRequestUpdate) -> None:
        if payload.request_from_date > payload.request_to_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="request_from_date cannot be after request_to_date")
        if payload.is_half_day and payload.request_from_date != payload.request_to_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Half-day request must be for one day")
        if payload.comments and len(payload.comments) > 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comments should not exceed 200 characters")

    def _working_days(self, from_date: date, to_date: date) -> list[date]:
        days: list[date] = []
        current = from_date
        while current <= to_date:
            if current.weekday() < 5 and not self._is_non_optional_holiday(current):
                days.append(current)
            current += timedelta(days=1)
        return days

    @staticmethod
    def _is_non_optional_holiday(day: date) -> bool:
        # Placeholder hook for holiday parity integration when holiday master is added.
        _ = day
        return False

    @staticmethod
    def _can_apply_leave(_user: User, _day: date) -> bool:
        # Legacy canApplyLeave currently behaves permissively.
        return True

    async def _is_user_on_bench(self, user_id: int) -> bool:
        today = date.today()
        async with self.db.session() as session:
            base_where = (
                Allocation.user_id == user_id,
                Allocation.is_active.is_(True),
                Allocation.start_date <= today,
                or_(Allocation.end_date.is_(None), Allocation.end_date >= today),
            )

            any_active_id = await session.scalar(select(Allocation.id).where(*base_where).limit(1))
            if any_active_id is None:
                return True

            any_non_bench_id = await session.scalar(
                select(Allocation.id)
                .join(Project, Allocation.project_id == Project.id)
                .where(
                    *base_where,
                    func.upper(Project.project_code).notin_(tuple(BENCH_EQUIVALENT_PROJECT_CODES)),
                )
                .limit(1)
            )
            return any_non_bench_id is None

    async def _manager_scope_for_user(self, user_id: int, at_date: date, client) -> list[tuple[int, int | None]]:
        allocs = (
            await client.scalars(
                select(Allocation).where(
                    Allocation.user_id == user_id,
                    Allocation.is_active.is_(True),
                    Allocation.start_date <= at_date,
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= at_date),
                )
            )
        ).all()
        if not allocs:
            return []
        project_ids = [a.project_id for a in allocs if a.project_id is not None]
        if not project_ids:
            return []
        rows = (
            await client.execute(
                select(UserRole.user_id, UserRole.project_id)
                .join(Role, UserRole.role_id == Role.id)
                .where(
                    UserRole.project_id.in_(project_ids),
                    Role.name.in_(["MANAGER", "ROLE_MANAGER"]),
                )
            )
        ).all()
        out: list[tuple[int, int | None]] = []
        seen: set[tuple[int, int | None]] = set()
        for manager_id, project_id in rows:
            key = (int(manager_id), int(project_id) if project_id is not None else None)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    async def _is_hr_user(self, user_id: int, client) -> bool:
        rows = (
            await client.execute(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
            )
        ).all()
        names = {str(row[0]).upper() for row in rows}
        return bool(names.intersection({"ROLE_HR", "HR"}))

    async def _initiated_manager_ids_for_request(self, user_request_id: int, client) -> set[int]:
        rows = (
            await client.execute(
                select(UserRequestTracking.actioner_id)
                .join(UserRole, UserRole.user_id == UserRequestTracking.actioner_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRequestTracking.user_request_id == user_request_id,
                    UserRequestTracking.action == "INITIATED",
                    Role.name.in_(["ROLE_MANAGER", "MANAGER"]),
                )
            )
        ).all()
        return {int(row[0]) for row in rows}

    async def _is_client_user(self, user_id: int, client) -> bool:
        rows = (
            await client.scalars(
                select(Allocation)
                .join(Project, Allocation.project_id == Project.id)
                .where(
                    Allocation.user_id == user_id,
                    Allocation.is_active.is_(True),
                    Project.project_code.notin_(list(BENCH_EQUIVALENT_PROJECT_CODES) + ["GLOBAL"]),
                    Project.project_type.in_(["CLIENT", "STAFFING"]),
                )
            )
        ).all()
        return len(rows) > 0

    async def _deduct_leave_for_date_range(
        self,
        *,
        user_id: int,
        user: User,
        user_request_id: int,
        from_date: date,
        to_date: date,
        is_half_day: bool,
        approver_id: int,
        client,
    ) -> None:
        tx_rows: list[dict] = []
        for day in self._working_days(from_date, to_date):
            if not self._can_apply_leave(user, day):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Leave not allowed on {day}")
            unit = 0.5 if is_half_day else 1.0
            mapping = await client.scalar(
                select(LeaveMapping).where(
                    LeaveMapping.user_id == user_id,
                    LeaveMapping.year == day.year,
                    LeaveMapping.month == day.month,
                )
            )
            if not mapping:
                mapping = LeaveMapping(
                    user_id=user_id,
                    year=day.year,
                    month=day.month,
                    primary_leave=0.0,
                    secondary_leave=0.0,
                    carry_forward=0.0,
                )
                client.add(mapping)
                await client.flush()
            primary = float(mapping.primary_leave or 0.0)
            secondary = float(mapping.secondary_leave or 0.0)
            remaining = float(unit)
            primary_deduct = min(max(primary, 0.0), remaining)
            remaining -= primary_deduct
            secondary_deduct = remaining
            mapping.primary_leave = primary - primary_deduct
            mapping.secondary_leave = secondary - secondary_deduct
            tx_rows.append(
                {
                    "user_request_id": user_request_id,
                    "user_id": user_id,
                    "transaction_type": "DEDUCT",
                    "for_date": day,
                    "value": unit,
                    "comments": f"[D:{primary_deduct}P,{secondary_deduct}S]",
                    "updated_by_id": approver_id,
                }
            )
        if tx_rows:
            await self.leave_tx_repo.create_many(tx_rows, client=client)

    async def _revert_leave_for_request(self, *, user_id: int, user_request_id: int, client) -> None:
        txns = await self.leave_tx_repo.list_by_user_request(user_request_id, client=client)
        deduct_txns = [t for t in txns if str(t.transaction_type).upper() == "DEDUCT"]
        for txn in deduct_txns:
            primary_restore = 0.0
            secondary_restore = float(txn.value or 0.0)
            comments = txn.comments or ""
            match = _DEDUCT_SPLIT_RE.search(comments)
            if match:
                primary_restore = float(match.group("primary"))
                secondary_restore = float(match.group("secondary"))
            mapping = await client.scalar(
                select(LeaveMapping).where(
                    LeaveMapping.user_id == user_id,
                    LeaveMapping.year == txn.for_date.year,
                    LeaveMapping.month == txn.for_date.month,
                )
            )
            if not mapping:
                mapping = LeaveMapping(
                    user_id=user_id,
                    year=txn.for_date.year,
                    month=txn.for_date.month,
                    primary_leave=0.0,
                    secondary_leave=0.0,
                    carry_forward=0.0,
                )
                client.add(mapping)
                await client.flush()
            mapping.primary_leave = float(mapping.primary_leave or 0.0) + primary_restore
            mapping.secondary_leave = float(mapping.secondary_leave or 0.0) + secondary_restore

            # Legacy-like rebalance: offset negative secondary by available primary.
            if float(mapping.secondary_leave or 0.0) < 0 and float(mapping.primary_leave or 0.0) > 0:
                transfer = min(float(mapping.primary_leave or 0.0), abs(float(mapping.secondary_leave or 0.0)))
                mapping.primary_leave = float(mapping.primary_leave or 0.0) - transfer
                mapping.secondary_leave = float(mapping.secondary_leave or 0.0) + transfer

            await client.delete(txn)
        await client.flush()

    async def _adjust_leave_balance(self, user_id: int, for_date: date, delta: float, client) -> None:
        mapping = await client.scalar(
            select(LeaveMapping).where(
                LeaveMapping.user_id == user_id,
                LeaveMapping.year == for_date.year,
                LeaveMapping.month == for_date.month,
            )
        )
        if not mapping:
            mapping = LeaveMapping(
                user_id=user_id,
                year=for_date.year,
                month=for_date.month,
                primary_leave=0.0,
                secondary_leave=0.0,
                carry_forward=0.0,
            )
            client.add(mapping)
            await client.flush()
        mapping.secondary_leave = float(mapping.secondary_leave or 0.0) + float(delta)
        await client.flush()

    def _to_out(self, row) -> UserRequestOut:
        return UserRequestOut(
            id=row.id,
            emp_email=row.user.email if row.user else "",
            request_from_date=row.request_from_date,
            request_to_date=row.request_to_date,
            comments=row.comments,
            request_type=row.request_type,
            status=row.status,
            is_half_day=row.is_half_day,
            reference_file_url=row.reference_file_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_request(self, actor_email: str, payload: UserRequestCreate) -> int:
        self._validate_request_payload(payload)
        user = await self._get_user_by_email_or_404(actor_email)
        request_type = payload.request_type.upper()

        if request_type == "WFH" and await self._is_user_on_bench(user.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WFH is not allowed while employee is on bench")

        if request_type in {"LEAVE", "WFH"}:
            days = self._working_days(payload.request_from_date, payload.request_to_date)
            if not days:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request range only contains weekends/holidays")
        if request_type == "LEAVE":
            async with self.db.session() as session:
                if await self._is_client_user(user.id, session) and payload.client_approval is not True:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client approval is required for client users.")
            for day in self._working_days(payload.request_from_date, payload.request_to_date):
                if not self._can_apply_leave(user, day):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Leave not allowed on {day}")

        overlaps = await self.request_repo.list_for_user_in_window(
            user_id=user.id,
            request_type=request_type,
            from_date=payload.request_from_date,
            to_date=payload.request_to_date,
        )
        for overlap in overlaps:
            if overlap.status in {"PENDING", "APPROVED"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{request_type} already pending/approved for this period")

        async with self.db.tx() as tx:
            row = await self.request_repo.create(
                {
                    "user_id": user.id,
                    "request_from_date": payload.request_from_date,
                    "request_to_date": payload.request_to_date,
                    "request_type": request_type,
                    "comments": payload.comments,
                    "status": "PENDING",
                    "is_half_day": payload.is_half_day,
                    "reference_file_url": payload.reference_file_url,
                    "manager_comp_off_email": payload.manager_comp_off_email,
                },
                client=tx,
            )

            manager_scope = await self._manager_scope_for_user(user.id, payload.request_from_date, tx)
            for manager_id, project_id in manager_scope:
                await self.tracking_repo.create(
                    {
                        "action": "INITIATED",
                        "user_request_id": row.id,
                        "actioner_id": manager_id,
                        "project_id": project_id,
                    },
                    client=tx,
                )
            await self.tracking_repo.create(
                {
                    "action": "INITIATED",
                    "user_request_id": row.id,
                    "actioner_id": user.id,
                    "project_id": None,
                },
                client=tx,
            )
            hr_users = await self.user_repo.list_users_by_role_names(["ROLE_HR", "HR"])
            recipients = {manager_id for manager_id, _ in manager_scope}
            recipients.update(u.id for u in hr_users)
            recipients.discard(user.id)
            await self.notification_service.send_notifications(
                receiver_ids=sorted(recipients),
                sender_id=user.id,
                notification_type=self._request_created_type(request_type),
                title=f"{request_type} Request Submitted",
                message=f"{user.name} submitted {request_type} request from {payload.request_from_date} to {payload.request_to_date}",
                client=tx,
            )

            # Email delivery happens after the DB transaction commits (parity with safer side effects).
            request_id = row.id
            manager_ids = sorted({manager_id for manager_id, _ in manager_scope})

        manager_emails: list[str] = []
        for manager_id in manager_ids:
            manager = await self.user_repo.get_by_id(manager_id)
            if manager and manager.email:
                manager_emails.append(manager.email)

        to_recipients = ["applyleave@webknot.in", *manager_emails]
        to_string = ";".join(to_recipients)
        subject = f"{request_type} Applied by {user.name}"
        reason = payload.comments if payload.comments is not None else "null"
        body = USER_REQUEST_SUBMIT % (
            "Manager",
            user.name,
            request_type,
            reason,
            payload.request_from_date,
            payload.request_to_date,
        )

        try:
            await self.email_service.send_email(
                to=to_string,
                subject=subject,
                body=body,
                cc=user.email,
                is_html=True,
            )
        except Exception:  # noqa: BLE001
            # Email delivery is a side effect; don't break request creation.
            pass

        return request_id

    async def list_requests(
        self,
        *,
        actor_email: str,
        actor_roles: set[str],
        from_date: date,
        to_date: date,
        request_type: str,
        page: int,
        size: int,
        emp_emails: list[str] | None = None,
    ) -> UserRequestListResponse:
        roles = _normalize_roles(actor_roles)
        actor = await self._get_user_by_email_or_404(actor_email)
        request_type = request_type.upper()
        target_ids: list[int] = []
        if emp_emails:
            users = [await self._get_user_by_email_or_404(email) for email in emp_emails]
            target_ids = [u.id for u in users]
        elif "ROLE_HR" in roles:
            async with self.db.session() as session:
                all_users = (await session.scalars(select(User))).all()
                target_ids = [u.id for u in all_users]
        elif "ROLE_MANAGER" in roles:
            rows, total = await self.request_repo.list_for_manager_scope(
                manager_email=actor.email,
                manager_user_id=actor.id,
                request_type=request_type,
                from_date=from_date,
                to_date=to_date,
                page=page,
                size=size,
            )
            visible_rows = [row for row in rows if row.user_id != actor.id]
            excluded_count = max(0, len(rows) - len(visible_rows))
            visible_total = max(0, total - excluded_count)
            return UserRequestListResponse(
                current_page=page,
                total_pages=(visible_total + size - 1) // size if size else 0,
                page_size=size,
                total_elements=visible_total,
                data=[self._to_out(r) for r in visible_rows],
            )
        else:
            target_ids = [actor.id]

        rows, total = await self.request_repo.list_for_users(
            user_ids=target_ids,
            from_date=from_date,
            to_date=to_date,
            request_type=request_type,
            page=page,
            size=size,
        )
        return UserRequestListResponse(
            current_page=page,
            total_pages=(total + size - 1) // size if size else 0,
            page_size=size,
            total_elements=total,
            data=[self._to_out(r) for r in rows],
        )

    async def update_status(self, actor_email: str, actor_roles: set[str], payload: UserRequestStatusUpdate) -> int:
        roles = _normalize_roles(actor_roles)
        approver = await self._get_user_by_email_or_404(actor_email)
        async with self.db.tx() as tx:
            row = await self.request_repo.get_by_id_with_lock(payload.user_request_id, tx)
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserRequest not found")
            if row.user_id == approver.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot be approved/rejected by yourself")

            action = payload.user_request_status.upper()
            if action not in {"APPROVED", "REJECTED"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")
            if action == "REJECTED" and not (payload.message and payload.message.strip()):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection message is required")

            request_type = str(row.request_type).upper()
            prior_actions_for_approver = await self.tracking_repo.list_by_request_and_actioner(row.id, approver.id)
            if any(str(track.action).upper() == action for track in prior_actions_for_approver):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You have already {action.title()} this request.")

            is_hr_approver = await self._is_hr_user(approver.id, tx)
            is_manager_approver = "ROLE_MANAGER" in roles
            if request_type in {"LEAVE", "WFH"}:
                if not is_hr_approver and not is_manager_approver:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Needs to be approved/rejected by a Project manager or an HR")
                if is_manager_approver:
                    allowed_manager_ids = await self._initiated_manager_ids_for_request(row.id, tx)
                    if approver.id not in allowed_manager_ids:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to update status of this request.")
                if not is_hr_approver:
                    hr_rejection = (
                        await tx.execute(
                            select(UserRequestTracking.id)
                            .join(UserRole, UserRole.user_id == UserRequestTracking.actioner_id)
                            .join(Role, Role.id == UserRole.role_id)
                            .where(
                                UserRequestTracking.user_request_id == row.id,
                                UserRequestTracking.action == "REJECTED",
                                Role.name.in_(["ROLE_HR", "HR"]),
                            )
                            .limit(1)
                        )
                    ).first()
                    if hr_rejection:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This request has already been rejected by HR.")

            if is_hr_approver:
                previous_status = str(row.status).upper()
                row.status = "APPROVED" if action == "APPROVED" else "REJECTED"
                if row.request_type == "LEAVE":
                    if action == "APPROVED":
                        await self._deduct_leave_for_date_range(
                            user_id=row.user_id,
                            user=row.user,
                            user_request_id=row.id,
                            from_date=row.request_from_date,
                            to_date=row.request_to_date,
                            is_half_day=row.is_half_day,
                            approver_id=approver.id,
                            client=tx,
                        )
                    else:
                        if previous_status == "APPROVED":
                            await self._revert_leave_for_request(
                                user_id=row.user_id,
                                user_request_id=row.id,
                                client=tx,
                            )
                elif row.request_type == "COMP_OFF" and action == "APPROVED":
                    await self.comp_off_service.grant_for_approved_request(
                        user_id=row.user_id,
                        user_request_id=row.id,
                        approved_by_id=approver.id,
                        request_date=row.request_from_date,
                        is_half_day=row.is_half_day,
                        client=tx,
                    )

            await self.tracking_repo.create(
                {
                    "action": action,
                    "user_request_id": row.id,
                    "actioner_id": approver.id,
                    "project_id": None,
                    "message": payload.message,
                },
                client=tx,
            )
            await self.notification_service.send_notification(
                receiver_id=row.user_id,
                sender_id=approver.id,
                notification_type=self._request_action_type(row.request_type, action),
                title=f"{row.request_type} Request {action.title()}",
                message=f"Your {row.request_type} request was {action.lower()}",
                client=tx,
            )

            # Capture email details; sending is a side effect after commit.
            request_id = row.id
            requestor_email = row.user.email if row.user else ""
            requestor_name = row.user.name if row.user else ""
            request_type_value = request_type
            request_from_date = row.request_from_date
            request_to_date = row.request_to_date

        try:
            subject = f"{request_type_value} {action} for {requestor_name}"
            body = USER_REQUEST_STATUS_UPDATE % (
                requestor_name,
                request_type_value.lower(),
                action.lower(),
                request_type_value,
                request_from_date,
                request_to_date,
                approver.name,
            )
            await self.email_service.send_email(
                to=requestor_email,
                subject=subject,
                body=body,
                cc="applyleave@webknot.in",
                is_html=True,
            )
        except Exception:  # noqa: BLE001
            # Email delivery is a side effect; don't break request status updates.
            pass

        return request_id

    async def update_request(self, actor_email: str, payload: UserRequestUpdate) -> int:
        self._validate_request_payload(payload)
        actor = await self._get_user_by_email_or_404(actor_email)
        async with self.db.tx() as tx:
            row = await self.request_repo.get_by_id_with_lock(payload.user_request_id, tx)
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserRequest not found")
            if row.user_id != actor.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized request")
            if row.status != "PENDING":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending requests can be updated")
            row.request_from_date = payload.request_from_date
            row.request_to_date = payload.request_to_date
            row.comments = payload.comments
            row.is_half_day = payload.is_half_day
            row.reference_file_url = payload.reference_file_url
            row.manager_comp_off_email = payload.manager_comp_off_email
            row.updated_at = datetime.utcnow()
            return row.id

    async def delete_request(self, actor_email: str, user_request_id: int) -> str:
        actor = await self._get_user_by_email_or_404(actor_email)
        async with self.db.tx() as tx:
            row = await self.request_repo.get_by_id_with_lock(user_request_id, tx)
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="UserRequest not found")
            if row.user_id != actor.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized request")
            if row.status != "PENDING":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending request can be deleted")
            row.deleted = True
            row.updated_at = datetime.utcnow()
            return "Deleted"
