import asyncio
from typing import Optional

from uuid_utils.compat import uuid4

from src.common.logger import log
from src.services.interfaces.pool import ConnectionPool
from src.services.interfaces.registry import ConnectionRegistry
from src.services.interfaces.storage import StreamStorage
from src.services.interfaces.transport import WebSocketTransport
from src.services.provider.websockets.datastructure import (
    Connection,
    ConnectionConfig,
    ConnectionState,
)
from src.services.provider.websockets.datastructure.connection import ConnectionMetadata
from src.services.provider.websockets.datastructure.message import RawMessage
from src.services.provider.websockets.registry import InMemoryConnectionRegistry
from src.services.provider.websockets.router import MessageRouter
from src.services.provider.websockets.storage import InMemoryStreamStorage
from src.services.provider.websockets.types import (
    ConnectionStateHandler,
    ErrorHandler,
)


class ConnectionService:
    def __init__(
        self,
        transport: WebSocketTransport,
        registry: ConnectionRegistry | None = None,
        message_router: MessageRouter | None = None,
        stream_storage: StreamStorage | None = None,
        pool: ConnectionPool | None = None,
    ) -> None:
        self._transport = transport
        self._pool = pool
        self._active_connections: dict[str, asyncio.Task[None]] = {}
        self._pool_to_transport: dict[str, str] = {}
        self._state_handlers: list[ConnectionStateHandler] = []
        self._error_handlers: list[ErrorHandler] = []
        self._registry = registry or InMemoryConnectionRegistry()
        self._message_router = message_router or MessageRouter()
        self._stream_storage = stream_storage or InMemoryStreamStorage()

    async def create_connection(self, config: ConnectionConfig) -> str:
        pool_connection_id: str | None = None

        if self._pool:
            pool_connection_id = await self._pool.acquire()
            if not pool_connection_id:
                raise RuntimeError("Connection pool exhausted")

        if not pool_connection_id:
            pool_connection_id = uuid4().hex

        try:
            transport_connection_id = await self._transport.connect(config)
            self._pool_to_transport[pool_connection_id] = transport_connection_id

            connection = Connection(
                id=pool_connection_id,
                uri=config.uri,
                state=ConnectionState.CONNECTED,
                metadata={"config": config, "transport_id": transport_connection_id},
            )

            await self._registry.save(connection)
            await self._notify_state_change(
                pool_connection_id, ConnectionState.CONNECTED, connection.metadata
            )

            task = asyncio.create_task(self._handle_connection(pool_connection_id))
            self._active_connections[pool_connection_id] = task

            return pool_connection_id

        except Exception:
            if self._pool:
                await self._pool.release(pool_connection_id)
            raise

    async def close_connection(self, connection_id: str) -> None:
        if task := self._active_connections.pop(connection_id, None):
            task.cancel()

        transport_id = self._pool_to_transport.pop(connection_id, None)
        if transport_id:
            await self._transport.disconnect(transport_id)

        await self._registry.delete(connection_id)
        if self._pool:
            await self._pool.release(connection_id)

        await self._stream_storage.remove(connection_id)
        await self._notify_state_change(connection_id, ConnectionState.DISCONNECTED)

    async def close_all(self) -> None:
        for connection_id in list(self._active_connections.keys()):
            await self.close_connection(connection_id)
            await self._stream_storage.remove(connection_id)

        if hasattr(self._transport, "close_all"):
            await self._transport.close_all()

    async def reconnect(self, connection_id: str) -> None:
        if task := self._active_connections.pop(connection_id, None):
            task.cancel()

        await self._notify_state_change(connection_id, ConnectionState.DISCONNECTED)
        await self._schedule_reconnect(connection_id)

    async def send_message(self, connection_id: str, data: str) -> bool:
        connection = await self._registry.get(connection_id)
        if not connection or connection.state != ConnectionState.CONNECTED:
            return False

        transport_id = self._pool_to_transport.get(connection_id, None)
        if not transport_id:
            return False

        return await self._transport.send(transport_id, data)

    async def get_connection_state(
        self, connection_id: str
    ) -> Optional[ConnectionState]:
        connection = await self._registry.get(connection_id)
        return connection.state if connection else None

    def add_state_handler(self, handler: ConnectionStateHandler) -> None:
        self._state_handlers.append(handler)

    def add_error_handler(self, handler: ErrorHandler) -> None:
        self._error_handlers.append(handler)

    async def add_stream(self, connection_id: str, stream_data: str) -> None:
        return await self._stream_storage.save(
            connection_id=connection_id, stream_data=stream_data
        )

    async def _handle_connection(self, connection_id: str) -> None:
        connection = await self._registry.get(connection_id)
        if not connection or not connection.metadata:
            return

        transport_id = connection.metadata["transport_id"]

        try:
            async for response in self._transport.receive(
                transport_id, timeout=connection.metadata["config"].connection_timeout
            ):
                message = RawMessage(
                    data=response,
                    connection_id=connection_id,
                    timestamp=asyncio.get_event_loop().time(),
                    metadata=connection.metadata,
                )
                await self._message_router.route_message(message)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error(
                "%-45s | conn_id: %s, error: %s",
                "Error in connection",
                connection_id,
                e,
            )
            await self._notify_error(connection_id, e, connection.metadata)
            await self._schedule_reconnect(connection_id)

    async def _schedule_reconnect(self, connection_id: str) -> None:
        connection = await self._registry.get(connection_id)
        if not connection or not connection.metadata:
            return

        config = connection.metadata["config"]

        log.info(
            "%-45s | url: %s , context: %s",
            "Schedule reconnect",
            connection.uri,
            config.context if config.context else None,
        )

        if connection.reconnect_attempts >= config.max_reconnect_attempts:
            await self._set_connection_state(
                connection_id, ConnectionState.FAILED, connection.metadata
            )
            return

        await self._set_connection_state(connection_id, ConnectionState.RECONNECTING)
        connection.reconnect_attempts += 1
        await self._registry.save(connection)

        await asyncio.sleep(config.reconnect_interval)

        try:
            old_transport_id = self._pool_to_transport.get(connection_id)

            if old_transport_id:
                await self._transport.disconnect(old_transport_id)

            new_transport_id = await self._transport.connect(config)
            self._pool_to_transport[connection_id] = new_transport_id

            connection.state = ConnectionState.CONNECTED
            connection.metadata = {
                "config": config,
                "transport_id": new_transport_id,
            }
            await self._registry.save(connection)

            task = asyncio.create_task(self._handle_connection(connection_id))
            self._active_connections[connection_id] = task

            await self._notify_state_change(
                connection_id, ConnectionState.CONNECTED, connection.metadata
            )
            asyncio.create_task(self._resubscribing_streams(connection_id))

            connection.reconnect_attempts = 0
            await self._registry.save(connection)

        except Exception as e:
            await self._notify_error(connection_id, e, connection.metadata)
            await self._set_connection_state(
                connection_id, ConnectionState.FAILED, connection.metadata
            )

    async def _set_connection_state(
        self,
        connection_id: str,
        state: ConnectionState,
        metadata: ConnectionMetadata | None = None,
    ) -> None:
        connection = await self._registry.get(connection_id)
        if connection:
            connection.state = state
            await self._registry.save(connection)
            await self._notify_state_change(connection_id, state, metadata)

    async def _notify_state_change(
        self,
        connection_id: str,
        state: ConnectionState,
        metadata: ConnectionMetadata | None = None,
    ) -> None:
        for handler in self._state_handlers:
            try:
                await handler(connection_id, state, metadata)
            except Exception:
                pass

    async def _notify_error(
        self,
        connection_id: str,
        error: Exception,
        metadata: ConnectionMetadata | None = None,
    ) -> None:
        for handler in self._error_handlers:
            await handler(connection_id, error, metadata)

    async def _resubscribing_streams(
        self,
        connection_id: str,
    ) -> None:
        streams_data = await self._stream_storage.get_all(connection_id)
        if not streams_data:
            return None

        for stream_data in streams_data:
            await self.send_message(
                connection_id,
                data=stream_data,
            )
