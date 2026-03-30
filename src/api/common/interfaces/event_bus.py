from typing import Protocol, runtime_checkable

from src.api.common.events.base import Event


@runtime_checkable
class EventBus(Protocol):
    async def publish(self, event: Event) -> None: ...
