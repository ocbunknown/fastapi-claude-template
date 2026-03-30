from typing import Optional
from urllib.parse import urljoin

from src.common.logger import log
from src.services.provider.websockets.datastructure import ConnectionConfig
from src.services.provider.websockets.router import MessageRouter
from src.services.provider.websockets.service import ConnectionService
from src.services.provider.websockets.types import (
    ConnectionStateHandler,
    ErrorHandler,
    MessageHandler,
)


class BaseWebSocketClient:
    def __init__(
        self,
        url: str,
        connection_service: ConnectionService,
        message_router: MessageRouter,
    ) -> None:
        self._url = url
        self._connection_service = connection_service
        self._message_router = message_router
        self._connections: dict[str, ConnectionConfig] = {}

    async def connect(self, config: ConnectionConfig) -> str:
        connection_id = await self._connection_service.create_connection(config)
        log.info("%-45s | conn_id: %s", f"Connect {config.uri}", connection_id)
        self._connections[connection_id] = config
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        if connection_id in self._connections:
            await self._connection_service.close_connection(connection_id)

    async def close_all(self) -> None:
        await self._connection_service.close_all()
        self._connections.clear()

    async def close(self, connection_id: str) -> None:
        await self._connection_service.close_connection(connection_id)
        self._connections.pop(connection_id, None)

    async def reconnect(self, connection_id: str) -> None:
        await self._connection_service.reconnect(connection_id)

    async def send_message(
        self,
        data: str,
        connection_id: Optional[str],
        resend_on_reconnect: bool = False,
    ) -> bool:
        if not connection_id:
            return False

        if resend_on_reconnect:
            await self._connection_service.add_stream(
                connection_id=connection_id,
                stream_data=data,
            )
        return await self._connection_service.send_message(connection_id, data)

    def add_message_handler(self, connection_id: str, handler: MessageHandler) -> None:
        self._message_router.add_handler(connection_id, handler)

    def add_global_message_handler(self, handler: MessageHandler) -> None:
        self._message_router.add_global_handler(handler)

    def add_connection_state_handler(self, handler: ConnectionStateHandler) -> None:
        self._connection_service.add_state_handler(handler)

    def add_error_handler(self, handler: ErrorHandler) -> None:
        self._connection_service.add_error_handler(handler)

    @property
    def is_connected(self) -> bool:
        return self._connections is not None

    def endpoint_url(self, endpoint: str) -> str:
        return urljoin(self._url, endpoint)
