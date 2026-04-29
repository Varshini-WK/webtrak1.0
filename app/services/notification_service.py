from __future__ import annotations

from fastapi import HTTPException, status

from app.domain.notification_types import NotificationType
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_stream_service import NotificationEvent, get_notification_stream_service


class NotificationService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.user_repo = UserRepository(db)
        self.stream = get_notification_stream_service()

    @staticmethod
    def _as_type(value: NotificationType | str) -> str:
        if isinstance(value, NotificationType):
            return value.value
        return str(value).strip().upper()

    @staticmethod
    def _to_out(row) -> dict:
        return {
            "id": row.id,
            "receiver_id": row.receiver_id,
            "sender_id": row.sender_id,
            "type": row.type,
            "title": row.title,
            "message": row.message,
            "is_read": row.is_read,
            "created_at": row.created_at.isoformat(),
        }

    async def _publish(self, row) -> None:
        await self.stream.publish(
            NotificationEvent(
                id=row.id,
                receiver_id=row.receiver_id,
                sender_id=row.sender_id,
                type=row.type,
                title=row.title,
                message=row.message,
                is_read=row.is_read,
                created_at=row.created_at.isoformat(),
            )
        )

    async def send_notification(
        self,
        *,
        receiver_id: int | None,
        sender_id: int | None,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        client=None,
    ):
        row = await self.repo.create(
            {
                "receiver_id": receiver_id,
                "sender_id": sender_id,
                "type": self._as_type(notification_type),
                "title": title,
                "message": message,
            },
            client=client,
        )
        # Push only when independent transaction is used to avoid phantom delivery on rollback.
        if client is None:
            await self._publish(row)
        return row

    async def send_notifications(
        self,
        *,
        receiver_ids: list[int],
        sender_id: int | None,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        client=None,
    ) -> list:
        payloads = [
            {
                "receiver_id": receiver_id,
                "sender_id": sender_id,
                "type": self._as_type(notification_type),
                "title": title,
                "message": message,
            }
            for receiver_id in sorted(set(receiver_ids))
        ]
        rows = await self.repo.create_many(payloads, client=client)
        if client is None:
            for row in rows:
                await self._publish(row)
        return rows

    async def list_notifications_for_actor(self, actor_email: str, page: int, size: int) -> dict:
        user = await self.user_repo.get_by_email(actor_email.lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        rows, total = await self.repo.list_for_user_page(user.id, page, size)
        return {
            "current_page": page,
            "total_pages": (total + size - 1) // size if size else 0,
            "page_size": size,
            "total_elements": total,
            "data": [self._to_out(row) for row in rows],
        }

    async def mark_read_for_actor(self, actor_email: str, notification_id: int) -> dict:
        user = await self.user_repo.get_by_email(actor_email.lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        row = await self.repo.mark_read(notification_id, user.id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return self._to_out(row)

    async def mark_all_read_for_actor(self, actor_email: str) -> int:
        user = await self.user_repo.get_by_email(actor_email.lower())
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return await self.repo.mark_all_read(user.id)

    async def announce(self, actor_email: str, title: str, message: str) -> dict:
        actor = await self.user_repo.get_by_email(actor_email.lower())
        if not actor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        recipients = await self.user_repo.list_all_users()
        receiver_ids = [u.id for u in recipients if u.id != actor.id]
        rows = await self.send_notifications(
            receiver_ids=receiver_ids,
            sender_id=actor.id,
            notification_type=NotificationType.ANNOUNCEMENT,
            title=title,
            message=message,
        )
        return {"sent": len(rows)}

    async def delete_read_notifications(self) -> int:
        return await self.repo.delete_read_notifications()
