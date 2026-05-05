from datetime import datetime

from sqlalchemy import and_, func, or_, select

from app.models.policy_document import PolicyDocument
from app.models.policy_recipient import PolicyRecipient
from app.models.user import User


class PolicyRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def create_policy(self, payload: dict, client=None) -> PolicyDocument:
        row = PolicyDocument(**payload)
        if client is not None:
            client.add(row)
            await client.flush()
            return row
        async with self.db.tx() as session:
            session.add(row)
            await session.flush()
            return row

    async def get_policy(self, policy_id: int, client=None) -> PolicyDocument | None:
        if client is not None:
            return await client.get(PolicyDocument, policy_id)
        async with self.db.session() as session:
            return await session.get(PolicyDocument, policy_id)

    async def update_policy_status(
        self,
        policy_id: int,
        *,
        status: str,
        published_at: datetime | None = None,
        client=None,
    ) -> PolicyDocument | None:
        row = await self.get_policy(policy_id, client=client)
        if row is None:
            return None
        row.status = status
        if published_at is not None:
            row.published_at = published_at
        if client is not None:
            await client.flush()
            return row
        async with self.db.tx() as session:
            db_row = await session.get(PolicyDocument, policy_id)
            if db_row is None:
                return None
            db_row.status = status
            if published_at is not None:
                db_row.published_at = published_at
            await session.flush()
            return db_row

    async def list_target_users(
        self,
        *,
        send_to_all: bool,
        departments: list[str],
        roles: list[str],
        user_ids: list[int],
    ) -> list[User]:
        async with self.db.session() as session:
            stmt = select(User).where(User.status.in_(["ACTIVE", "ONBOARDING", "INVITED"]))
            if send_to_all:
                return list((await session.scalars(stmt.order_by(User.id.asc()))).all())
            filters = []
            if departments:
                filters.append(User.department.in_(departments))
            if roles:
                filters.append(User.role.in_(roles))
            if user_ids:
                filters.append(User.id.in_(user_ids))
            if not filters:
                return []
            stmt = stmt.where(or_(*filters)).order_by(User.id.asc())
            rows = list((await session.scalars(stmt)).all())
            dedup = {row.id: row for row in rows}
            return list(dedup.values())

    async def bulk_create_recipients(self, payloads: list[dict], client=None) -> list[PolicyRecipient]:
        rows = [PolicyRecipient(**payload) for payload in payloads]
        if not rows:
            return []
        if client is not None:
            client.add_all(rows)
            await client.flush()
            return rows
        async with self.db.tx() as session:
            session.add_all(rows)
            await session.flush()
            return rows

    async def get_recipient(self, *, policy_id: int, user_id: int, client=None) -> PolicyRecipient | None:
        stmt = select(PolicyRecipient).where(
            PolicyRecipient.policy_id == policy_id,
            PolicyRecipient.user_id == user_id,
        )
        if client is not None:
            return await client.scalar(stmt)
        async with self.db.session() as session:
            return await session.scalar(stmt)

    async def list_user_policies(self, *, user_id: int) -> list[tuple[PolicyDocument, PolicyRecipient]]:
        async with self.db.session() as session:
            stmt = (
                select(PolicyDocument, PolicyRecipient)
                .join(PolicyRecipient, PolicyRecipient.policy_id == PolicyDocument.id)
                .where(PolicyRecipient.user_id == user_id)
                .order_by(PolicyDocument.created_at.desc(), PolicyDocument.id.desc())
            )
            return list((await session.execute(stmt)).all())

    async def mark_viewed(self, *, policy_id: int, user_id: int, now: datetime, client=None) -> PolicyRecipient | None:
        row = await self.get_recipient(policy_id=policy_id, user_id=user_id, client=client)
        if row is None:
            return None
        if row.viewed_at is None:
            row.viewed_at = now
        if row.status in {"SENT", "PENDING"}:
            row.status = "VIEWED"
        if client is not None:
            await client.flush()
            return row
        async with self.db.tx() as session:
            db_row = await session.scalar(
                select(PolicyRecipient).where(
                    PolicyRecipient.policy_id == policy_id,
                    PolicyRecipient.user_id == user_id,
                )
            )
            if db_row is None:
                return None
            if db_row.viewed_at is None:
                db_row.viewed_at = now
            if db_row.status in {"SENT", "PENDING"}:
                db_row.status = "VIEWED"
            await session.flush()
            return db_row

    async def mark_signed(
        self,
        *,
        policy_id: int,
        user_id: int,
        now: datetime,
        signed_file_url: str,
        client=None,
    ) -> PolicyRecipient | None:
        row = await self.get_recipient(policy_id=policy_id, user_id=user_id, client=client)
        if row is None:
            return None
        if row.viewed_at is None:
            row.viewed_at = now
        row.signed_at = now
        row.signed_file_url = signed_file_url
        row.status = "SIGNED"
        if client is not None:
            await client.flush()
            return row
        async with self.db.tx() as session:
            db_row = await session.scalar(
                select(PolicyRecipient).where(
                    PolicyRecipient.policy_id == policy_id,
                    PolicyRecipient.user_id == user_id,
                )
            )
            if db_row is None:
                return None
            if db_row.viewed_at is None:
                db_row.viewed_at = now
            db_row.signed_at = now
            db_row.signed_file_url = signed_file_url
            db_row.status = "SIGNED"
            await session.flush()
            return db_row

    async def list_policy_recipients_with_user(self, *, policy_id: int) -> list[tuple[PolicyRecipient, User]]:
        async with self.db.session() as session:
            stmt = (
                select(PolicyRecipient, User)
                .join(User, User.id == PolicyRecipient.user_id)
                .where(PolicyRecipient.policy_id == policy_id)
                .order_by(User.name.asc(), User.email.asc())
            )
            return list((await session.execute(stmt)).all())

    async def list_signed_documents(self, *, policy_id: int) -> list[tuple[int, str, str, str]]:
        async with self.db.session() as session:
            stmt = (
                select(User.id, User.name, User.email, PolicyRecipient.signed_file_url)
                .join(User, User.id == PolicyRecipient.user_id)
                .where(
                    PolicyRecipient.policy_id == policy_id,
                    PolicyRecipient.signed_file_url.is_not(None),
                )
                .order_by(User.name.asc())
            )
            return [(int(uid), str(name), str(email), str(url)) for uid, name, email, url in (await session.execute(stmt)).all()]

    async def mark_pending_overdue(self, *, now: datetime) -> int:
        async with self.db.tx() as session:
            stmt = (
                select(PolicyRecipient)
                .join(PolicyDocument, PolicyDocument.id == PolicyRecipient.policy_id)
                .where(
                    PolicyDocument.status == "PUBLISHED",
                    PolicyDocument.deadline_at.is_not(None),
                    PolicyDocument.deadline_at < now,
                    PolicyRecipient.status != "SIGNED",
                )
            )
            rows = list((await session.scalars(stmt)).all())
            for row in rows:
                row.status = "PENDING"
            await session.flush()
            return len(rows)

    async def list_pending_recipients_with_policy(self, *, now: datetime) -> list[tuple[PolicyRecipient, PolicyDocument]]:
        async with self.db.session() as session:
            stmt = (
                select(PolicyRecipient, PolicyDocument)
                .join(PolicyDocument, PolicyDocument.id == PolicyRecipient.policy_id)
                .where(
                    PolicyDocument.status == "PUBLISHED",
                    PolicyDocument.deadline_at.is_not(None),
                    PolicyDocument.deadline_at < now,
                    PolicyRecipient.status != "SIGNED",
                )
            )
            return list((await session.execute(stmt)).all())
