import abc
from typing import Self

from src.api.common.interfaces.mediator import Mediator
from src.api.common.websockets.query import WebsocketQuery
from src.services.provider.websockets.datastructure.message import RawMessage


class WebsocketEventRouter[E](abc.ABC):
    def __init__(self, mediator: Mediator | None = None) -> None:
        self.mediator = mediator
        self._handlers: dict[E, type[WebsocketQuery]] = {}

    async def __call__(self, message: RawMessage) -> None:
        return await self.route(message)

    async def route(self, message: RawMessage) -> None:
        assert self.mediator, "Mediator is not set"

        event_type = self._resolve_event_type(message)
        if not event_type:
            return

        query = self._handlers[event_type]
        await self.mediator.send(query(message=message))

    def provide(self, mediator: Mediator) -> Self:
        self.mediator = mediator
        return self

    def register(self, event_type: E, query: type[WebsocketQuery]) -> None:
        self._handlers[event_type] = query

    @abc.abstractmethod
    def _resolve_event_type(self, message: RawMessage) -> E | None:
        raise NotImplementedError
