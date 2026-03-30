from typing import Awaitable, Callable

from src.services.provider.websockets.datastructure import (
    ConnectionMetadata,
    ConnectionState,
    RawMessage,
)

MessageHandler = Callable[[RawMessage], Awaitable[None]]
ConnectionStateHandler = Callable[
    [str, ConnectionState, ConnectionMetadata | None], Awaitable[None]
]
ErrorHandler = Callable[[str, Exception, ConnectionMetadata | None], Awaitable[None]]
