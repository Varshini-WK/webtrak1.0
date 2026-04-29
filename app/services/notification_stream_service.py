from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class NotificationEvent:
    id: int
    receiver_id: int | None
    sender_id: int | None
    type: str
    title: str
    message: str | None
    is_read: bool
    created_at: str


class NotificationStreamService:
    def __init__(self) -> None:
        self._queues: dict[int, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._queues[user_id].add(queue)
        return queue

    async def unsubscribe(self, user_id: int, queue: asyncio.Queue) -> None:
        async with self._lock:
            if user_id in self._queues:
                self._queues[user_id].discard(queue)
                if not self._queues[user_id]:
                    del self._queues[user_id]

    async def publish(self, event: NotificationEvent) -> None:
        receiver_id = event.receiver_id
        if receiver_id is None:
            return
        async with self._lock:
            queues = list(self._queues.get(receiver_id, set()))
        stale: list[asyncio.Queue] = []
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop saturated consumers to preserve overall delivery health.
                stale.append(queue)
        for queue in stale:
            await self.unsubscribe(receiver_id, queue)


_notification_stream_service = NotificationStreamService()


def get_notification_stream_service() -> NotificationStreamService:
    return _notification_stream_service

