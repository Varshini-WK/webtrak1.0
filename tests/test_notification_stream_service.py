import asyncio

from app.services.notification_stream_service import NotificationEvent, NotificationStreamService


def test_stream_subscribe_publish_unsubscribe() -> None:
    async def _run() -> None:
        service = NotificationStreamService()
        queue = await service.subscribe(101)
        await service.publish(
            NotificationEvent(
                id=1,
                receiver_id=101,
                sender_id=2,
                type="LEAVE_REQUEST",
                title="Title",
                message="Message",
                is_read=False,
                created_at="2026-01-01T00:00:00",
            )
        )
        event = await asyncio.wait_for(queue.get(), timeout=1)
        assert event.id == 1
        await service.unsubscribe(101, queue)

    asyncio.run(_run())

