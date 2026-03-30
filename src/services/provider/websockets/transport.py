import asyncio
import ssl
from contextlib import suppress
from typing import Any, AsyncIterator, Optional

import aiohttp
import certifi
from aiohttp import ClientWebSocketResponse
from uuid_utils.compat import uuid4

from src.common.logger import log
from src.services.interfaces.transport import WebSocketTransport
from src.services.provider.websockets.datastructure import ConnectionConfig
from src.services.provider.websockets.datastructure.message import Response


class AioHttpWebSocketTransport(WebSocketTransport):
    def __init__(self, **connector_init: Any) -> None:
        self._connections: dict[str, ClientWebSocketResponse] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector_type: type[aiohttp.TCPConnector] = aiohttp.TCPConnector
        self._connector_init: dict[str, Any] = {
            "ssl": ssl.create_default_context(cafile=certifi.where()),
            "limit": 1000,
            "limit_per_host": 1000,
            "ttl_dns_cache": 300,
            "use_dns_cache": True,
        } | connector_init

    async def create_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=self._connector_type(**self._connector_init),
            )

        return self._session

    async def connect(self, config: ConnectionConfig) -> str:
        session = await self.create_session()
        retries = 0
        delay = 1

        while True:
            try:
                websocket = await asyncio.wait_for(
                    session.ws_connect(
                        config.uri,
                        headers=config.headers or {},
                        heartbeat=config.ping_interval,
                        proxy=config.proxy,
                        timeout=aiohttp.ClientWSTimeout(
                            ws_receive=config.connection_timeout
                        ),
                    ),
                    timeout=10.0,
                )
                connection_id = uuid4().hex
                self._connections[connection_id] = websocket
                return connection_id

            except Exception as e:
                retries += 1
                if retries > config.max_connection_retries:
                    raise ConnectionError(
                        f"WebSocket connection failed after {config.max_connection_retries} retries: {e}"
                    ) from e
                log.error(
                    "Connection to '%s' was FAILED, retry in %s seconds, left retries %s",
                    config.uri,
                    delay,
                    config.max_connection_retries - retries,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    async def disconnect(self, connection_id: str) -> None:
        websocket = self._connections.pop(connection_id, None)

        if websocket:
            try:
                await asyncio.wait_for(websocket.close(), timeout=5.0)
            except (TimeoutError, Exception):
                pass

    async def send(self, connection_id: str, data: str) -> bool:
        websocket = self._connections.get(connection_id)
        if not websocket:
            return False

        try:
            await asyncio.wait_for(websocket.send_str(data), timeout=5.0)
            return True
        except Exception:
            return False

    def receive(
        self, connection_id: str, *, timeout: Optional[int] = None
    ) -> AsyncIterator[Response]:
        return self._async_receive(connection_id, timeout=timeout)

    async def _async_receive(
        self, connection_id: str, *, timeout: Optional[int] = None
    ) -> AsyncIterator[Response]:
        websocket = self._connections.get(connection_id)
        if not websocket:
            return

        try:
            while True:
                try:
                    message = await websocket.receive(timeout=timeout)

                    if message.type in (
                        aiohttp.WSMsgType.TEXT,
                        aiohttp.WSMsgType.BINARY,
                    ):
                        yield Response(message.data)
                    elif message.type in (
                        aiohttp.WSMsgType.CLOSE,
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        log.warning(
                            "%-45s | conn_id: %s",
                            "WebSocket closed by server",
                            connection_id,
                        )
                        raise ConnectionError("WebSocket closed by server")

                except TimeoutError:
                    log.warning(
                        "%-45s | conn_id: %s, timeout: %s seconds",
                        "No message received (timeout)",
                        connection_id,
                        timeout,
                    )
                    raise ConnectionError(
                        f"No message received within {timeout} seconds"
                    ) from None
        finally:
            self._connections.pop(connection_id, None)
            if not websocket.closed:
                with suppress(Exception):
                    await websocket.close()

    async def is_alive(self, connection_id: str) -> bool:
        websocket = self._connections.get(connection_id)
        if not websocket:
            return False

        try:
            return not websocket.closed
        except Exception:
            return False

    async def close_all(self) -> None:
        for connection_id in list(self._connections.keys()):
            await self.disconnect(connection_id)

        if self._session is not None and not self._session.closed:
            await self._session.close()
            await asyncio.sleep(0.25)
