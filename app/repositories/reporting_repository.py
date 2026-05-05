from __future__ import annotations

from datetime import date

from sqlalchemy import and_, func, or_, select

from app.models.allocation import Allocation
from app.models.document import Document
from app.models.project import Project
from app.models.user import User
from app.models.user_profile import UserProfile


class ReportingRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def list_users_for_workforce_overview(
        self,
        *,
        search: str | None,
        statuses: list[str],
    ) -> list[User]:
        async with self.db.session() as session:
            stmt = select(User).where(User.status.in_(statuses))
            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        User.name.ilike(term),
                        User.email.ilike(term),
                        User.emp_id.ilike(term),
                        User.department.ilike(term),
                        User.role.ilike(term),
                    )
                )
            stmt = stmt.order_by(User.id.asc())
            return list((await session.scalars(stmt)).all())

    async def list_active_allocation_billing_statuses(self) -> list[tuple[int, str | None]]:
        today = date.today()
        async with self.db.session() as session:
            stmt = (
                select(Allocation.user_id, Allocation.billing_status)
                .where(
                    Allocation.is_active.is_(True),
                    Allocation.start_date <= today,
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= today),
                )
                .order_by(Allocation.user_id.asc(), Allocation.id.asc())
            )
            return list((await session.execute(stmt)).all())

    async def list_profile_yoe(self, user_ids: list[int]) -> dict[int, int]:
        if not user_ids:
            return {}
        async with self.db.session() as session:
            stmt = select(UserProfile.user_id, UserProfile.yoe).where(
                and_(
                    UserProfile.user_id.in_(user_ids),
                    UserProfile.yoe.is_not(None),
                )
            )
            rows = list((await session.execute(stmt)).all())
        return {int(user_id): int(yoe) for user_id, yoe in rows if yoe is not None}

    async def list_active_allocations_for_users(
        self,
        *,
        user_ids: list[int],
        as_of: date,
    ) -> list[tuple[int, int, str | None, str, date]]:
        if not user_ids:
            return []
        async with self.db.session() as session:
            stmt = (
                select(
                    Allocation.user_id,
                    Allocation.allocated_hours,
                    Allocation.billing_status,
                    Project.project_code,
                    Allocation.start_date,
                )
                .join(Project, Project.id == Allocation.project_id)
                .where(
                    Allocation.user_id.in_(user_ids),
                    Allocation.is_active.is_(True),
                    Allocation.start_date <= as_of,
                    or_(Allocation.end_date.is_(None), Allocation.end_date >= as_of),
                )
                .order_by(Allocation.user_id.asc(), Allocation.id.asc())
            )
            return list((await session.execute(stmt)).all())

    async def list_users_for_skill_inventory(
        self,
        *,
        search: str | None,
        statuses: list[str],
    ) -> list[tuple[int, str | None, str, str, str | None, str | None, list[str] | None, list[dict] | None]]:
        async with self.db.session() as session:
            stmt = (
                select(
                    User.id,
                    User.emp_id,
                    User.email,
                    User.name,
                    User.department,
                    User.role,
                    UserProfile.primary_skills,
                    UserProfile.secondary_skills,
                )
                .outerjoin(UserProfile, UserProfile.user_id == User.id)
                .where(User.status.in_(statuses))
            )
            if search and search.strip():
                term = f"%{search.strip()}%"
                stmt = stmt.where(
                    or_(
                        User.name.ilike(term),
                        User.email.ilike(term),
                        User.emp_id.ilike(term),
                        User.department.ilike(term),
                        User.role.ilike(term),
                    )
                )
            stmt = stmt.order_by(User.name.asc(), User.email.asc())
            return list((await session.execute(stmt)).all())

    async def list_certification_documents_by_users(self, *, user_ids: list[int]) -> list[tuple[int, str]]:
        if not user_ids:
            return []
        async with self.db.session() as session:
            stmt = (
                select(Document.user_id, Document.file_url)
                .where(
                    Document.user_id.in_(user_ids),
                    Document.doc_type == "CERTIFICATION",
                )
                .order_by(Document.user_id.asc(), Document.created_at.asc(), Document.id.asc())
            )
            return list((await session.execute(stmt)).all())

    async def count_workforce_by_employment_type(self, *, statuses: list[str]) -> list[tuple[str, int]]:
        async with self.db.session() as session:
            stmt = (
                select(User.user_type, func.count(User.id))
                .where(User.status.in_(statuses))
                .group_by(User.user_type)
                .order_by(User.user_type.asc())
            )
            return [(str(user_type or "UNKNOWN"), int(count)) for user_type, count in (await session.execute(stmt)).all()]

