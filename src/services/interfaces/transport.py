from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from src.services.provider.websockets.datastructure import ConnectionConfig
from src.services.provider.websockets.datastructure.message import Response


class WebSocketTransport(ABC):
    @abstractmethod
    async def connect(self, config: ConnectionConfig) -> str: ...

    @abstractmethod
    async def disconnect(self, connection_id: str) -> None: ...

    @abstractmethod
    async def send(self, connection_id: str, data: str) -> bool: ...

    @abstractmethod
    def receive(
        self, connection_id: str, *, timeout: Optional[int] = None
    ) -> AsyncIterator[Response]: ...

    @abstractmethod
    async def is_alive(self, connection_id: str) -> bool: ...
