from datetime import datetime, timedelta

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import selectinload

from app.models.training_assessment import TrainingAssessment
from app.models.training_attendance import TrainingAttendance
from app.models.training_material import TrainingMaterial
from app.models.training_participant_assessment import TrainingParticipantAssessment
from app.models.training import Training
from app.models.training_participant import TrainingParticipant
from app.models.training_session import TrainingSession
from app.models.training_trainer import TrainingTrainer
from app.models.user import User


class LearningRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create_training(self, payload: dict, client=None) -> Training:
        row = Training(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def update_training(self, training_id: int, payload: dict, client=None) -> Training | None:
        if client is not None:
            row = await client.get(Training, training_id)
            if not row:
                return None
            for k, v in payload.items():
                setattr(row, k, v)
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.get(Training, training_id)
            if not row:
                return None
            for k, v in payload.items():
                setattr(row, k, v)
            await session.flush()
            return row

    async def get_training(self, training_id: int) -> Training | None:
        async with self.db.session() as session:
            return await session.scalar(
                select(Training)
                .where(Training.id == training_id)
                .options(
                    selectinload(Training.trainers),
                    selectinload(Training.sessions),
                    selectinload(Training.participants),
                )
            )

    async def list_trainings(self, *, only_scheduled: bool = False) -> list[Training]:
        async with self.db.session() as session:
            stmt = select(Training).options(selectinload(Training.trainers)).order_by(Training.id.desc())
            if only_scheduled:
                stmt = stmt.where(Training.status == "SCHEDULED")
            return list((await session.scalars(stmt)).all())

    async def add_trainer(self, training_id: int, trainer_user_id: int, client=None) -> TrainingTrainer:
        row = TrainingTrainer(training_id=training_id, trainer_user_id=trainer_user_id)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def remove_trainer(self, training_id: int, trainer_user_id: int, client=None) -> int:
        stmt = delete(TrainingTrainer).where(
            TrainingTrainer.training_id == training_id,
            TrainingTrainer.trainer_user_id == trainer_user_id,
        )
        if client is not None:
            result = await client.execute(stmt)
            return int(result.rowcount or 0)
        async with self.db.tx() as session:
            result = await session.execute(stmt)
            return int(result.rowcount or 0)

    async def create_session(self, payload: dict, client=None) -> TrainingSession:
        row = TrainingSession(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_sessions(self, training_id: int) -> list[TrainingSession]:
        async with self.db.session() as session:
            stmt = (
                select(TrainingSession)
                .where(TrainingSession.training_id == training_id)
                .order_by(TrainingSession.session_date.asc(), TrainingSession.start_time.asc())
            )
            return list((await session.scalars(stmt)).all())

    async def add_participant(self, training_id: int, user_id: int, source: str, client=None) -> TrainingParticipant:
        row = TrainingParticipant(training_id=training_id, user_id=user_id, participant_source=source)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def remove_participant(self, training_id: int, user_id: int, client=None) -> int:
        stmt = delete(TrainingParticipant).where(
            TrainingParticipant.training_id == training_id,
            TrainingParticipant.user_id == user_id,
        )
        if client is not None:
            result = await client.execute(stmt)
            return int(result.rowcount or 0)
        async with self.db.tx() as session:
            result = await session.execute(stmt)
            return int(result.rowcount or 0)

    async def participant_exists(self, training_id: int, user_id: int) -> bool:
        async with self.db.session() as session:
            stmt = (
                select(func.count())
                .select_from(TrainingParticipant)
                .where(TrainingParticipant.training_id == training_id, TrainingParticipant.user_id == user_id)
            )
            return int((await session.scalar(stmt)) or 0) > 0

    async def list_participants(self, training_id: int) -> list[TrainingParticipant]:
        async with self.db.session() as session:
            stmt = select(TrainingParticipant).where(TrainingParticipant.training_id == training_id).order_by(TrainingParticipant.id.asc())
            return list((await session.scalars(stmt)).all())

    async def update_participant_status(self, training_id: int, user_id: int, enrollment_status: str, client=None) -> TrainingParticipant | None:
        if client is not None:
            row = await client.scalar(
                select(TrainingParticipant).where(
                    TrainingParticipant.training_id == training_id,
                    TrainingParticipant.user_id == user_id,
                )
            )
            if not row:
                return None
            row.enrollment_status = enrollment_status
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.scalar(
                select(TrainingParticipant).where(
                    TrainingParticipant.training_id == training_id,
                    TrainingParticipant.user_id == user_id,
                )
            )
            if not row:
                return None
            row.enrollment_status = enrollment_status
            await session.flush()
            return row

    async def list_active_user_ids_for_department(self, department: str) -> list[int]:
        async with self.db.session() as session:
            stmt = select(User.id).where(
                and_(
                    User.department == department,
                    User.status.in_(["ACTIVE", "ONBOARDING", "INVITED"]),
                )
            )
            return [int(x) for x in (await session.scalars(stmt)).all()]

    async def list_all_active_user_ids(self) -> list[int]:
        async with self.db.session() as session:
            stmt = select(User.id).where(User.status.in_(["ACTIVE", "ONBOARDING", "INVITED"]))
            return [int(x) for x in (await session.scalars(stmt)).all()]

    async def list_training_participant_user_ids(self, training_id: int) -> list[int]:
        async with self.db.session() as session:
            stmt = select(TrainingParticipant.user_id).where(TrainingParticipant.training_id == training_id)
            return [int(x) for x in (await session.scalars(stmt)).all()]

    async def list_sessions_in_next_hours(self, *, hours: int) -> list[TrainingSession]:
        now = datetime.utcnow()
        end = now + timedelta(hours=hours)
        async with self.db.session() as session:
            stmt = (
                select(TrainingSession)
                .where(TrainingSession.session_date >= now.date(), TrainingSession.session_date <= end.date())
                .order_by(TrainingSession.session_date.asc(), TrainingSession.start_time.asc())
            )
            return list((await session.scalars(stmt)).all())

    async def create_material(self, payload: dict, client=None) -> TrainingMaterial:
        row = TrainingMaterial(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_materials(self, training_id: int, *, include_hr_only: bool) -> list[TrainingMaterial]:
        async with self.db.session() as session:
            stmt = select(TrainingMaterial).where(TrainingMaterial.training_id == training_id)
            if not include_hr_only:
                stmt = stmt.where(TrainingMaterial.visibility == "EMPLOYEE")
            stmt = stmt.order_by(TrainingMaterial.id.asc())
            return list((await session.scalars(stmt)).all())

    async def upsert_attendance(self, payload: dict, client=None) -> TrainingAttendance:
        stmt = select(TrainingAttendance).where(
            TrainingAttendance.training_session_id == payload["training_session_id"],
            TrainingAttendance.user_id == payload["user_id"],
        )
        if client is not None:
            row = await client.scalar(stmt)
            if row is None:
                row = TrainingAttendance(**payload)
                client.add(row)
            else:
                row.attendance_status = payload["attendance_status"]
                row.marked_by = payload.get("marked_by")
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.scalar(stmt)
            if row is None:
                row = TrainingAttendance(**payload)
                session.add(row)
            else:
                row.attendance_status = payload["attendance_status"]
                row.marked_by = payload.get("marked_by")
            await session.flush()
            return row

    async def list_attendance_for_session(self, training_session_id: int) -> list[TrainingAttendance]:
        async with self.db.session() as session:
            stmt = select(TrainingAttendance).where(TrainingAttendance.training_session_id == training_session_id).order_by(TrainingAttendance.id.asc())
            return list((await session.scalars(stmt)).all())

    async def create_assessment(self, payload: dict, client=None) -> TrainingAssessment:
        row = TrainingAssessment(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def list_assessments(self, training_id: int) -> list[TrainingAssessment]:
        async with self.db.session() as session:
            stmt = select(TrainingAssessment).where(TrainingAssessment.training_id == training_id).order_by(TrainingAssessment.id.asc())
            return list((await session.scalars(stmt)).all())

    async def total_assessment_weight(self, training_id: int) -> int:
        async with self.db.session() as session:
            stmt = select(func.coalesce(func.sum(TrainingAssessment.weight_percent), 0)).where(TrainingAssessment.training_id == training_id)
            return int((await session.scalar(stmt)) or 0)

    async def upsert_participant_assessment(self, payload: dict, client=None) -> TrainingParticipantAssessment:
        stmt = select(TrainingParticipantAssessment).where(
            TrainingParticipantAssessment.training_id == payload["training_id"],
            TrainingParticipantAssessment.user_id == payload["user_id"],
        )
        if client is not None:
            row = await client.scalar(stmt)
            if row is None:
                row = TrainingParticipantAssessment(**payload)
                client.add(row)
            else:
                for key, value in payload.items():
                    setattr(row, key, value)
            await client.flush()
            return row
        async with self.db.tx() as session:
            row = await session.scalar(stmt)
            if row is None:
                row = TrainingParticipantAssessment(**payload)
                session.add(row)
            else:
                for key, value in payload.items():
                    setattr(row, key, value)
            await session.flush()
            return row

    async def get_participant_assessment(self, training_id: int, user_id: int) -> TrainingParticipantAssessment | None:
        async with self.db.session() as session:
            stmt = select(TrainingParticipantAssessment).where(
                TrainingParticipantAssessment.training_id == training_id,
                TrainingParticipantAssessment.user_id == user_id,
            )
            return await session.scalar(stmt)

    async def get_session(self, training_session_id: int) -> TrainingSession | None:
        async with self.db.session() as session:
            return await session.get(TrainingSession, training_session_id)

    async def get_participant(self, training_id: int, user_id: int) -> TrainingParticipant | None:
        async with self.db.session() as session:
            stmt = select(TrainingParticipant).where(
                TrainingParticipant.training_id == training_id,
                TrainingParticipant.user_id == user_id,
            )
            return await session.scalar(stmt)

