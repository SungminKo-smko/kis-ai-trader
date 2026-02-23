import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import uuid4

logger = logging.getLogger("event_bus")


@dataclass
class Event:
    type: str
    payload: Any
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable[..., Coroutine]]] = defaultdict(list)
        self._log = logger

    def subscribe(self, event_type: str, handler: Callable[..., Coroutine]):
        self._handlers[event_type].append(handler)
        self._log.info(f"Subscribed {handler.__name__} to {event_type}")

    async def publish(self, event: Event):
        self._log.info(f"[{event.source}] → {event.type}")
        handlers = self._handlers.get(event.type, [])
        await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True
        )

    async def publish_and_wait(self, event: Event) -> list[Any]:
        handlers = self._handlers.get(event.type, [])
        results = await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)
        return [r for r in results if not isinstance(r, Exception)]


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
