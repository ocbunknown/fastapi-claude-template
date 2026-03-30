from collections import defaultdict
from typing import Sequence

from src.services.interfaces.storage import StreamStorage


class InMemoryStreamStorage(StreamStorage):
    def __init__(self) -> None:
        self._storage: defaultdict[str, set[str]] = defaultdict(set)

    async def save(self, connection_id: str, stream_data: str) -> None:
        self._storage[connection_id].add(stream_data)

    async def get_all(self, connection_id: str) -> Sequence[str] | None:
        streams = self._storage.get(connection_id)
        return list(streams) if streams else None

    async def remove(self, connection_id: str) -> None:
        self._storage.pop(connection_id, None)

    async def remove_all(self) -> None:
        self._storage.clear()
