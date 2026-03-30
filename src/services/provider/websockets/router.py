import asyncio
from collections import defaultdict

from src.services.provider.websockets.datastructure.message import RawMessage
from src.services.provider.websockets.types import MessageHandler


class MessageRouter:
    def __init__(self) -> None:
        self._handlers: defaultdict[str, list[MessageHandler]] = defaultdict(list)
        self._global_handlers: list[MessageHandler] = []

    def add_handler(self, connection_id: str, handler: MessageHandler) -> None:
        self._handlers[connection_id].append(handler)

    def add_global_handler(self, handler: MessageHandler) -> None:
        self._global_handlers.append(handler)

    def remove_handler(self, connection_id: str, handler: MessageHandler) -> None:
        try:
            self._handlers[connection_id].remove(handler)
        except ValueError:
            pass

    async def route_message(self, message: RawMessage) -> None:
        tasks = []

        connection_handlers = self._handlers.get(message.connection_id, [])
        for handler in connection_handlers:
            tasks.append(asyncio.shield(self._safe_handle(handler, message)))

        for handler in self._global_handlers:
            tasks.append(asyncio.shield(self._safe_handle(handler, message)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_handle(self, handler: MessageHandler, message: RawMessage) -> None:
        try:
            await handler(message)
        except Exception:
            pass
