import asyncio
from typing import Optional

from uuid_utils.compat import uuid4

from src.services.interfaces.pool import ConnectionPool


class AsyncConnectionPool(ConnectionPool):
    def __init__(self, max_connections: int = 10000) -> None:
        self._max_connections = max_connections
        self._semaphore = asyncio.Semaphore(max_connections)
        self._active_connections: set[str] = set()

    async def acquire(self) -> Optional[str]:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=1.0)
        except TimeoutError:
            return None

        connection_id = uuid4().hex
        self._active_connections.add(connection_id)
        return connection_id

    async def release(self, connection_id: str) -> bool:
        if connection_id in self._active_connections:
            self._active_connections.remove(connection_id)
            self._semaphore.release()
            return True

        return False
