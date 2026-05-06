from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, UploadFile, status

from app.domain.notification_types import NotificationType
from app.repositories.learning_repository import LearningRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.profile_repository import ProfileRepository
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
        self.profile_repo = ProfileRepository(db)

    @staticmethod
    def _to_file_url(file: UploadFile) -> str:
        timestamp = int(datetime.now(UTC).timestamp())
        return f"local://uploads/{timestamp}_{file.filename}"

    @staticmethod
    def _validate_pdf(file: UploadFile, field_name: str) -> None:
        name = (file.filename or "").lower()
        if not name.endswith(".pdf"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} must be a PDF file")

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

    async def add_material(self, training_id: int, *, title: str, visibility: str, material_file: UploadFile, actor_roles: set[str]):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        self._validate_pdf(material_file, "material_file")
        row = await self.repo.create_material(
            {
                "training_id": training_id,
                "title": title.strip(),
                "material_url": self._to_file_url(material_file),
                "visibility": visibility,
            }
        )
        return {
            "id": row.id,
            "training_id": row.training_id,
            "title": row.title,
            "material_url": row.material_url,
            "visibility": row.visibility,
        }

    async def list_materials(self, training_id: int, *, actor_roles: set[str]):
        roles = _normalize_actor_roles(actor_roles)
        include_hr = bool({"ROLE_HR", "ROLE_ADMIN"} & roles)
        rows = await self.repo.list_materials(training_id, include_hr_only=include_hr)
        return [
            {
                "id": row.id,
                "training_id": row.training_id,
                "title": row.title,
                "material_url": row.material_url,
                "visibility": row.visibility,
            }
            for row in rows
        ]

    async def mark_attendance(self, training_id: int, training_session_id: int, payload, *, actor_user_id: int, actor_roles: set[str]):
        self._require_hr(actor_roles)
        session = await self.repo.get_session(training_session_id)
        if not session or session.training_id != training_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
        participant = await self.repo.get_participant(training_id, payload.user_id)
        if not participant:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a participant of this training")
        row = await self.repo.upsert_attendance(
            {
                "training_session_id": training_session_id,
                "training_id": training_id,
                "user_id": payload.user_id,
                "attendance_status": payload.attendance_status,
                "marked_by": actor_user_id,
            }
        )
        return {
            "id": row.id,
            "training_session_id": row.training_session_id,
            "training_id": row.training_id,
            "user_id": row.user_id,
            "attendance_status": row.attendance_status,
        }

    async def list_session_attendance(self, training_id: int, training_session_id: int, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        session = await self.repo.get_session(training_session_id)
        if not session or session.training_id != training_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training session not found")
        rows = await self.repo.list_attendance_for_session(training_session_id)
        return [
            {
                "id": row.id,
                "training_session_id": row.training_session_id,
                "training_id": row.training_id,
                "user_id": row.user_id,
                "attendance_status": row.attendance_status,
            }
            for row in rows
        ]

    async def create_assessment(
        self,
        training_id: int,
        *,
        name: str,
        description: str | None,
        weight_percent: int,
        assessment_file: UploadFile,
        actor_roles: set[str],
    ):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        self._validate_pdf(assessment_file, "assessment_file")
        if weight_percent < 1 or weight_percent > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="weight_percent must be between 1 and 100")
        current_total = await self.repo.total_assessment_weight(training_id)
        if current_total + weight_percent > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Total assessment weight cannot exceed 100")
        row = await self.repo.create_assessment(
            {
                "training_id": training_id,
                "name": name.strip(),
                "description": description,
                "file_url": self._to_file_url(assessment_file),
                "weight_percent": weight_percent,
            }
        )
        return {
            "id": row.id,
            "training_id": row.training_id,
            "name": row.name,
            "description": row.description,
            "file_url": row.file_url,
            "weight_percent": row.weight_percent,
        }

    async def list_assessments(self, training_id: int):
        rows = await self.repo.list_assessments(training_id)
        return [
            {
                "id": row.id,
                "training_id": row.training_id,
                "name": row.name,
                "description": row.description,
                "file_url": row.file_url,
                "weight_percent": row.weight_percent,
            }
            for row in rows
        ]

    @staticmethod
    def _skill_tier(score: float) -> tuple[str, int]:
        if score >= 90:
            return "ADVANCED", 5
        if score >= 75:
            return "INTERMEDIATE", 4
        if score >= 50:
            return "BASIC", 3
        return "FOUNDATION", 2

    async def _apply_skill_update(self, training, user_id: int, final_score: float, client) -> None:
        tier, rating = self._skill_tier(final_score)
        profile = await self.profile_repo.get_or_create_profile(user_id, client=client)
        existing = list(profile.secondary_skills or [])
        skill_key = (training.name or "").strip() or "Training Skill"
        updated = False
        for idx, entry in enumerate(existing):
            if str(entry.get("skill", "")).strip().lower() == skill_key.lower():
                existing[idx] = {"skill": skill_key, "rating": rating, "level": tier}
                updated = True
                break
        if not updated:
            existing.append({"skill": skill_key, "rating": rating, "level": tier})
        await self.profile_repo.update_profile(user_id, {"secondarySkills": existing}, client=client)

    async def upsert_participant_scores(self, training_id: int, payload, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")
        participant = await self.repo.get_participant(training_id, payload.user_id)
        if not participant:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a participant of this training")

        assessments = await self.repo.list_assessments(training_id)
        by_id = {str(a.id): a for a in assessments}
        if not by_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No assessments configured")
        unknown = [k for k in payload.scores_json.keys() if k not in by_id]
        if unknown:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown assessment ids in scores: {unknown}")
        total_weight = sum(a.weight_percent for a in assessments)
        if total_weight != 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment weight must total 100 before scoring")

        weighted = 0.0
        for key, score in payload.scores_json.items():
            if score < 0 or score > 100:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scores must be between 0 and 100")
            weighted += (score * by_id[key].weight_percent) / 100.0
        final_score = round(weighted, 2)

        async with self.db.tx() as tx:
            row = await self.repo.upsert_participant_assessment(
                {
                    "training_id": training_id,
                    "user_id": payload.user_id,
                    "scores_json": payload.scores_json,
                    "final_score_percent": final_score,
                    "is_completed": bool(payload.mark_completed),
                    "completed_at": datetime.utcnow() if payload.mark_completed else None,
                },
                client=tx,
            )
            if payload.mark_completed:
                await self.repo.update_participant_status(training_id, payload.user_id, "COMPLETED", client=tx)
                await self._apply_skill_update(training, payload.user_id, final_score, tx)
        return {
            "id": row.id,
            "training_id": row.training_id,
            "user_id": row.user_id,
            "scores_json": row.scores_json,
            "final_score_percent": row.final_score_percent,
            "is_completed": row.is_completed,
        }

    async def get_training_analytics(self, training_id: int, *, actor_roles: set[str]):
        self._require_hr(actor_roles)
        training = await self.repo.get_training(training_id)
        if not training:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training not found")

        participants = await self.repo.list_participants(training_id)
        enrolled_count = len(participants)
        completed_from_status = {p.user_id for p in participants if p.enrollment_status == "COMPLETED"}
        score_values: list[float] = []
        completed_from_scores: set[int] = set()
        for p in participants:
            pa = await self.repo.get_participant_assessment(training_id, p.user_id)
            if pa and pa.final_score_percent is not None:
                score_values.append(float(pa.final_score_percent))
            if pa and pa.is_completed:
                completed_from_scores.add(p.user_id)
        completed_count = len(completed_from_status.union(completed_from_scores))

        sessions = await self.repo.list_sessions(training_id)
        session_ids = {s.id for s in sessions}
        attendance_rows = []
        for s in sessions:
            attendance_rows.extend(await self.repo.list_attendance_for_session(s.id))
        relevant_attendance = [a for a in attendance_rows if a.training_session_id in session_ids and a.user_id in {p.user_id for p in participants}]
        present_count = sum(1 for a in relevant_attendance if a.attendance_status == "PRESENT")
        attendance_percent = 0.0
        if relevant_attendance:
            attendance_percent = round((present_count / len(relevant_attendance)) * 100.0, 2)

        avg_score = round(sum(score_values) / len(score_values), 2) if score_values else 0.0
        return {
            "training_id": training_id,
            "enrolled_count": enrolled_count,
            "completed_count": completed_count,
            "average_score_percent": avg_score,
            "average_attendance_percent": attendance_percent,
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

