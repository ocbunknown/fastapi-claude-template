from __future__ import annotations

from types import TracebackType
from typing import Optional, Protocol, Self, Type


class AsyncContextManager(Protocol):
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None: ...

    async def __aenter__(self) -> AsyncContextManager: ...


class BaseGateway:
    __slots__ = ("_context_manager",)

    def __init__(self, context_manager: AsyncContextManager) -> None:
        self._context_manager = context_manager

    async def __aenter__(self) -> Self:
        await self._context_manager.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self._context_manager.__aexit__(exc_type, exc_value, traceback)


