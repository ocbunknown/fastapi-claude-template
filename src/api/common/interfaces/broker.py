from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from src.api.common.events.base import Event


@dataclass
class BrokerMessage: ...


@runtime_checkable
class Broker[E: Event, M: BrokerMessage](Protocol):
    async def publish(self, message: M) -> None: ...

    def _build_message(self, event: E) -> M: ...


type BrokerType = Broker[Any, Any]
