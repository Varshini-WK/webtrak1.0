from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.domain.notification_types import NotificationType
from app.repositories.learning_repository import LearningRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService


def _normalize_actor_roles(actor_roles: set[str]) -> set[str]:
    out: set[str] = set()
    for role in actor_roles:
        r = role.strip().upper()
        if not r.startswith("ROLE_"):
            r = f"ROLE_{r}"
        out.add(r)
    return out


class LearningService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = LearningRepository(db)
        self.notification_service = NotificationService(db)
        self.notification_repo = NotificationRepository(db)

    @staticmethod
    def _require_hr(actor_roles: set[str]) -> None:
        roles = _normalize_actor_roles(actor_roles)
        if "ROLE_HR" not in roles and "ROLE_ADMIN" not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only HR/Admin can perform this action")

    async def _build_training_out(self, training):
        return {
            "id": training.id,
            "name": training.name,
            "category": training.category,
            "type": training.type,
            "description": training.description,
            "duration_days": training.duration_days,
            "status": training.status,
            "trainer_user_ids": [t.trainer_user_id for t in getattr(training, "trainers", [])],
        }

    async def create_training(self, payload, *, actor_user_id: int, actor_roles: set[str]):
        self._require_hr(actor_roles)
        row = await self.repo.create_training(
            {
                "name": payload.name.strip(),
                "category": payload.category,
                "type": payload.type,
                "description": payload.description,
                "duration_days": payload.duration_days,
                "status": "DRAFT",
                "created_by": actor_user_id,
            }
        )
        training = await self.repo.get_training(row.id)
        return await self._build_training_out(training)

    async def update_training(self, training_id: int, payload, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        update = payload.model_dump(exclude_none=True)
        if "name" in update:
            update["name"] = update["name"].strip()
        row = await self.repo.update_training(training_id, update)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        if update.get("status") == "SCHEDULED":
            await self.send_scheduled_notifications(training_id)
        training = await self.repo.get_training(training_id)
        return await self._build_training_out(training)

    async def list_trainings(self, *, actor_roles: set[str], only_scheduled: bool = False):
        rows = await self.repo.list_trainings(only_scheduled=only_scheduled)
        return [await self._build_training_out(row) for row in rows]

    async def assign_trainers(self, training_id: int, trainer_user_ids: list[int], *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        async with self.db.tx() as tx:
            for user_id in sorted(set(trainer_user_ids)):
                await self.repo.add_trainer(training_id, user_id, client=tx)
        refreshed = await self.repo.get_training(training_id)
        return await self._build_training_out(refreshed)

    async def remove_trainer(self, training_id: int, trainer_user_id: int, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        deleted = await self.repo.remove_trainer(training_id, trainer_user_id)
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer assignment not found")
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        return await self._build_training_out(training)

    async def create_session(self, training_id: int, payload, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        row = await self.repo.create_session(
            {
                "training_id": training_id,
                "session_date": payload.session_date,
                "start_time": payload.start_time,
                "end_time": payload.end_time,
                "mode": payload.mode,
                "venue": payload.venue,
                "meeting_link": payload.meeting_link,
            }
        )
        if training.status == "SCHEDULED":
            await self.send_scheduled_notifications(training_id)
        return {
            "id": row.id,
            "training_id": row.training_id,
            "session_date": row.session_date,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "mode": row.mode,
            "venue": row.venue,
            "meeting_link": row.meeting_link,
        }

    async def list_sessions(self, training_id: int, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        rows = await self.repo.list_sessions(training_id)
        return [
            {
                "id": row.id,
                "training_id": row.training_id,
                "session_date": row.session_date,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "mode": row.mode,
                "venue": row.venue,
                "meeting_link": row.meeting_link,
            }
            for row in rows
        ]

    async def assign_participants(self, training_id: int, payload, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        target_user_ids: list[int] = sorted(set(payload.user_ids))
        if payload.department:
            dept_ids = await self.repo.list_active_user_ids_for_department(payload.department)
            target_user_ids = sorted(set(target_user_ids).union(dept_ids))
        if payload.select_all:
            all_ids = await self.repo.list_all_active_user_ids()
            target_user_ids = sorted(set(target_user_ids).union(all_ids))
        if not target_user_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No participants resolved")
        async with self.db.tx() as tx:
            for user_id in target_user_ids:
                exists = await self.repo.participant_exists(training_id, user_id)
                if not exists:
                    await self.repo.add_participant(training_id, user_id, "ASSIGNED", client=tx)
        rows = await self.repo.list_participants(training_id)
        return [
            {
                "id": row.id,
                "training_id": row.training_id,
                "user_id": row.user_id,
                "participant_source": row.participant_source,
                "enrollment_status": row.enrollment_status,
            }
            for row in rows
        ]

    async def remove_participant(self, training_id: int, user_id: int, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        deleted = await self.repo.remove_participant(training_id, user_id)
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
        return {"removed": True}

    async def update_participant_status(self, training_id: int, user_id: int, enrollment_status: str, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        row = await self.repo.update_participant_status(training_id, user_id, enrollment_status)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
        return {
            "id": row.id,
            "training_id": row.training_id,
            "user_id": row.user_id,
            "participant_source": row.participant_source,
            "enrollment_status": row.enrollment_status,
        }

    async def self_enroll(self, training_id: int, *, actor_user_id: int):
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        if training.status != "SCHEDULED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only scheduled trainings are open")
        if training.type not in {"OPTIONAL", "HYBRID"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Self-enroll allowed only for optional/hybrid")
        if await self.repo.participant_exists(training_id, actor_user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already enrolled/assigned")
        row = await self.repo.add_participant(training_id, actor_user_id, "SELF_ENROLLED")
        return {
            "id": row.id,
            "training_id": row.training_id,
            "user_id": row.user_id,
            "participant_source": row.participant_source,
            "enrollment_status": row.enrollment_status,
        }

    async def list_open_trainings_for_employee(self):
        rows = await self.repo.list_trainings(only_scheduled=True)
        open_rows = [row for row in rows if row.type in {"OPTIONAL", "HYBRID"}]
        return [await self._build_training_out(row) for row in open_rows]

    async def send_scheduled_notifications(self, training_id: int) -> int:
        training = await self.repo.get_training(training_id)
        if not training:
            return 0
        sessions = await self.repo.list_sessions(training_id)
        if not sessions:
            return 0
        first_session = sessions[0]
        participant_user_ids = await self.repo.list_training_participant_user_ids(training_id)
        if not participant_user_ids:
            return 0
        dt = f"{first_session.session_date.isoformat()} {first_session.start_time.strftime('%H:%M')}"
        location_text = first_session.meeting_link if first_session.mode in {"ONLINE", "HYBRID"} else (first_session.venue or "TBD")
        title = f"Training Scheduled: {training.name}"
        message = f"{training.name} is scheduled on {dt}. Location: {location_text}."
        rows = await self.notification_service.send_notifications(
            receiver_ids=participant_user_ids,
            sender_id=None,
            notification_type=NotificationType.TRAINING_SCHEDULED,
            title=title,
            message=message,
        )
        return len(rows)

    async def send_training_reminders(self) -> int:
        rows = await self.repo.list_sessions_in_next_hours(hours=24)
        if not rows:
            return 0
        sent = 0
        now = datetime.now(UTC).replace(tzinfo=None)
        for session in rows:
            session_dt = datetime.combine(session.session_date, session.start_time)
            if session_dt <= now or session_dt > now + timedelta(hours=24):
                continue
            training = await self.repo.get_training(session.training_id)
            if not training:
                continue
            users = await self.repo.list_training_participant_user_ids(training.id)
            if not users:
                continue
            title = f"Training Reminder: {training.name}"
            location_text = session.meeting_link if session.mode in {"ONLINE", "HYBRID"} else (session.venue or "TBD")
            msg = f"Reminder: {training.name} starts at {session.start_time.strftime('%H:%M')} on {session.session_date.isoformat()} ({location_text})."
            day_start = datetime.combine(session.session_date, datetime.min.time())
            day_end = datetime.combine(session.session_date, datetime.max.time())
            receiver_ids: list[int] = []
            for user_id in users:
                already = await self.notification_repo.exists_for_receiver_sender_type_between(
                    receiver_id=user_id,
                    sender_id=None,
                    notification_type=NotificationType.TRAINING_REMINDER.value,
                    start_at=day_start,
                    end_at=day_end,
                )
                if not already:
                    receiver_ids.append(user_id)
            if receiver_ids:
                created = await self.notification_service.send_notifications(
                    receiver_ids=receiver_ids,
                    sender_id=None,
                    notification_type=NotificationType.TRAINING_REMINDER,
                    title=title,
                    message=msg,
                )
                sent += len(created)
        return sent

