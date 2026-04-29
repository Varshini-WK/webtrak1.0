import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.notification_service import NotificationService


def test_send_notifications_dedup_receivers() -> None:
    async def _run() -> None:
        service = NotificationService(MagicMock())
        service.repo.create_many = AsyncMock(return_value=[])  # type: ignore[method-assign]
        await service.send_notifications(
            receiver_ids=[3, 3, 5],
            sender_id=1,
            notification_type="ANNOUNCEMENT",
            title="Hello",
            message="World",
            client=object(),
        )
        payloads = service.repo.create_many.call_args.args[0]
        assert len(payloads) == 2

    asyncio.run(_run())


def test_send_notification_publishes_only_without_client() -> None:
    async def _run() -> None:
        service = NotificationService(MagicMock())
        fake_row = type(
            "N",
            (),
            {
                "id": 1,
                "receiver_id": 2,
                "sender_id": 1,
                "type": "LEAVE_REQUEST",
                "title": "t",
                "message": "m",
                "is_read": False,
                "created_at": type("D", (), {"isoformat": lambda self: "2026-01-01T00:00:00"})(),
            },
        )()
        service.repo.create = AsyncMock(return_value=fake_row)  # type: ignore[method-assign]
        service.stream.publish = AsyncMock()  # type: ignore[method-assign]

        await service.send_notification(
            receiver_id=2,
            sender_id=1,
            notification_type="LEAVE_REQUEST",
            title="t",
            message="m",
        )
        assert service.stream.publish.await_count == 1

        await service.send_notification(
            receiver_id=2,
            sender_id=1,
            notification_type="LEAVE_REQUEST",
            title="t",
            message="m",
            client=object(),
        )
        assert service.stream.publish.await_count == 1

    asyncio.run(_run())

