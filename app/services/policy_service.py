from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
import zipfile

from fastapi import HTTPException, UploadFile, status

from app.domain.notification_types import NotificationType
from app.repositories.policy_repository import PolicyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.policy import (
    PolicyComplianceReport,
    PolicyCreateRequest,
    PolicyListItem,
    PolicyPublishRequest,
    PolicyRecipientItem,
)
from app.services.notification_service import NotificationService


class PolicyService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = PolicyRepository(db)
        self.user_repo = UserRepository(db)
        self.notification_service = NotificationService(db)

    @staticmethod
    def _to_file_url(file: UploadFile) -> str:
        timestamp = int(datetime.now(UTC).timestamp())
        return f"local://uploads/{timestamp}_{file.filename}"

    async def create_policy(self, *, actor_email: str, payload: PolicyCreateRequest, document: UploadFile) -> dict:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        row = await self.repo.create_policy(
            {
                "title": payload.title.strip(),
                "description": payload.description,
                "file_url": self._to_file_url(document),
                "status": "DRAFT",
                "deadline_at": payload.deadline_at,
                "created_by": int(actor.id),
            }
        )
        return {"policy_id": row.id, "title": row.title, "status": row.status}

    async def publish_policy(self, *, actor_email: str, policy_id: int, payload: PolicyPublishRequest) -> dict:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        policy = await self.repo.get_policy(policy_id)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        if policy.status == "CLOSED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Closed policy cannot be published")

        users = await self.repo.list_target_users(
            send_to_all=payload.send_to_all,
            departments=payload.department_filters,
            roles=payload.role_filters,
            user_ids=payload.user_ids,
        )
        if not users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No target users resolved")

        now = datetime.utcnow()
        async with self.db.tx() as tx:
            row = await self.repo.get_policy(policy_id, client=tx)
            if row is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
            row.status = "PUBLISHED"
            row.published_at = now
            recipient_payloads = [
                {
                    "policy_id": int(policy_id),
                    "user_id": int(user.id),
                    "delivery_channel": payload.delivery_channel.upper(),
                    "sent_at": now,
                    "status": "SENT",
                }
                for user in users
            ]
            recipients = await self.repo.bulk_create_recipients(recipient_payloads, client=tx)
            await self.notification_service.send_notifications(
                receiver_ids=[int(user.id) for user in users],
                sender_id=int(actor.id),
                notification_type=NotificationType.POLICY_SENT,
                title=f"Policy sent: {row.title}",
                message="Please review and upload signed copy before deadline.",
                client=tx,
            )
        return {"policy_id": policy_id, "status": "PUBLISHED", "sent": len(recipients)}

    async def list_my_policies(self, *, actor_email: str) -> list[PolicyListItem]:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        rows = await self.repo.list_user_policies(user_id=int(actor.id))
        return [
            PolicyListItem(
                policy_id=policy.id,
                title=policy.title,
                status=recipient.status,
                deadline_at=policy.deadline_at,
                sent_at=recipient.sent_at,
                viewed_at=recipient.viewed_at,
                signed_at=recipient.signed_at,
                signed_file_url=recipient.signed_file_url,
            )
            for policy, recipient in rows
        ]

    async def mark_viewed(self, *, actor_email: str, policy_id: int) -> dict:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        row = await self.repo.mark_viewed(policy_id=policy_id, user_id=int(actor.id), now=datetime.utcnow())
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy recipient not found")
        await self.notification_service.send_notification(
            receiver_id=None,
            sender_id=int(actor.id),
            notification_type=NotificationType.POLICY_VIEWED,
            title="Policy viewed",
            message=f"User {actor.email} viewed policy #{policy_id}",
        )
        return {"policy_id": policy_id, "status": row.status, "viewed_at": row.viewed_at}

    async def upload_signed_copy(self, *, actor_email: str, policy_id: int, signed_copy: UploadFile) -> dict:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if actor is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        now = datetime.utcnow()
        row = await self.repo.mark_signed(
            policy_id=policy_id,
            user_id=int(actor.id),
            now=now,
            signed_file_url=self._to_file_url(signed_copy),
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy recipient not found")
        await self.notification_service.send_notification(
            receiver_id=None,
            sender_id=int(actor.id),
            notification_type=NotificationType.POLICY_SIGNED,
            title="Policy signed",
            message=f"User {actor.email} signed policy #{policy_id}",
        )
        return {"policy_id": policy_id, "status": row.status, "signed_file_url": row.signed_file_url}

    async def get_policy_compliance(self, *, policy_id: int) -> PolicyComplianceReport:
        policy = await self.repo.get_policy(policy_id)
        if policy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
        rows = await self.repo.list_policy_recipients_with_user(policy_id=policy_id)
        recipients: list[PolicyRecipientItem] = []
        sent_count = viewed_count = signed_count = pending_count = 0
        now = datetime.utcnow()
        for recipient, user in rows:
            status_token = recipient.status
            if status_token == "SENT":
                sent_count += 1
            if status_token in {"VIEWED", "SIGNED"}:
                viewed_count += 1
            if status_token == "SIGNED":
                signed_count += 1
            is_pending = status_token != "SIGNED" and policy.deadline_at is not None and policy.deadline_at < now
            if is_pending:
                pending_count += 1
            recipients.append(
                PolicyRecipientItem(
                    user_id=int(user.id),
                    employee_name=user.name,
                    email=user.email,
                    department=user.department,
                    role=user.role,
                    status="PENDING" if is_pending else status_token,
                    sent_at=recipient.sent_at,
                    viewed_at=recipient.viewed_at,
                    signed_at=recipient.signed_at,
                    signed_file_url=recipient.signed_file_url,
                )
            )
        total = len(recipients)
        return PolicyComplianceReport(
            policy_id=int(policy.id),
            title=policy.title,
            deadline_at=policy.deadline_at,
            total_recipients=total,
            sent_count=sent_count,
            viewed_count=viewed_count,
            signed_count=signed_count,
            pending_count=pending_count,
            signed_percentage=round((signed_count * 100.0 / total), 2) if total else 0.0,
            recipients=recipients,
        )

    async def list_signed_documents(self, *, policy_id: int) -> list[dict]:
        rows = await self.repo.list_signed_documents(policy_id=policy_id)
        return [{"user_id": uid, "name": name, "email": email, "signed_file_url": url} for uid, name, email, url in rows]

    async def export_signed_documents(self, *, policy_id: int) -> dict:
        rows = await self.repo.list_signed_documents(policy_id=policy_id)
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for uid, name, _email, url in rows:
                archive.writestr(f"{uid}_{name.replace(' ', '_')}.txt", url)
        return {"policy_id": policy_id, "file_name": f"policy_{policy_id}_signed_docs.zip", "content_base64": buffer.getvalue().hex()}

    async def send_pending_reminders(self) -> int:
        now = datetime.utcnow()
        rows = await self.repo.list_pending_recipients_with_policy(now=now)
        sent = 0
        for recipient, policy in rows:
            await self.notification_service.send_notification(
                receiver_id=int(recipient.user_id),
                sender_id=int(policy.created_by),
                notification_type=NotificationType.POLICY_PENDING_REMINDER,
                title=f"Pending policy acknowledgement: {policy.title}",
                message="Please upload your signed copy.",
            )
            sent += 1
        return sent

    async def mark_overdue_pending(self) -> int:
        return await self.repo.mark_pending_overdue(now=datetime.utcnow())
