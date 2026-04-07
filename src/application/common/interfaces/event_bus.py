from typing import Protocol, runtime_checkable

from src.application.common.events.base import Event
from src.application.common.interfaces.bus import Bus
from src.application.common.interfaces.wrapper import EventWrapper


@runtime_checkable
class EventBus(Bus[Event], Protocol):
    async def send(self, message: Event) -> None: ...
    async def send_wrapped(
        self,
        wrapper: EventWrapper,
        message: Event,
    ) -> None: ...
