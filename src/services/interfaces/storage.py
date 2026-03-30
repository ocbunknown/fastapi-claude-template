from abc import ABC, abstractmethod
from typing import Sequence


class StreamStorage(ABC):
    @abstractmethod
    async def save(self, connection_id: str, stream_data: str) -> None: ...

    @abstractmethod
    async def get_all(self, connection_id: str) -> Sequence[str] | None: ...

    @abstractmethod
    async def remove(self, connection_id: str) -> None: ...

    @abstractmethod
    async def remove_all(self) -> None: ...
