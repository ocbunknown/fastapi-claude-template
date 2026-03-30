from typing import Optional

from src.services.interfaces.registry import ConnectionRegistry
from src.services.provider.websockets.datastructure import Connection, ConnectionState


class InMemoryConnectionRegistry(ConnectionRegistry):
    def __init__(self) -> None:
        self._connections: dict[str, Connection] = {}
        self._active_connections: set[str] = set()

    async def save(self, connection: Connection) -> None:
        self._connections[connection.id] = connection
        if connection.state == ConnectionState.CONNECTED:
            self._active_connections.add(connection.id)

    async def get(self, connection_id: str) -> Optional[Connection]:
        return self._connections.get(connection_id)

    async def delete(self, connection_id: str) -> None:
        connection = self._connections.pop(connection_id, None)
        if connection:
            self._active_connections.discard(connection.id)

    async def get_all_active(self) -> list[Connection]:
        return [
            conn
            for conn in self._connections.values()
            if conn.state == ConnectionState.CONNECTED
        ]
