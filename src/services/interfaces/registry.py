from abc import ABC, abstractmethod
from typing import Optional

from src.services.provider.websockets.datastructure import Connection


class ConnectionRegistry(ABC):
    @abstractmethod
    async def save(self, connection: Connection) -> None: ...

    @abstractmethod
    async def get(self, connection_id: str) -> Optional[Connection]: ...

    @abstractmethod
    async def delete(self, connection_id: str) -> None: ...

    @abstractmethod
    async def get_all_active(self) -> list[Connection]: ...
