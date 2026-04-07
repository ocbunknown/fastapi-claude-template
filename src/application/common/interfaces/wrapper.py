from typing import Protocol, runtime_checkable

from src.application.common.events.base import Event
from src.application.common.interfaces.broker import BrokerType
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request


@runtime_checkable
class RequestWrapper[Q: Request, R](Protocol):
    async def execute(self, use_case: UseCase[Q, R], message: Q, /) -> R: ...


@runtime_checkable
class EventWrapper(Protocol):
    async def execute(self, broker: BrokerType, message: Event, /) -> None: ...
