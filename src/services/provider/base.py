from __future__ import annotations

import abc
from collections.abc import AsyncIterator, Mapping
from types import TracebackType
from typing import (
    Any,
    Final,
    Optional,
)

from src.services.provider.middleware.base import RequestMiddlewareType
from src.services.provider.middleware.manager import RequestMiddlewareManager
from src.services.provider.response import Response
from src.services.provider.types import RequestMethodType

DEFAULT_CHUNK_SIZE: Final[int] = 65536  # 50 mb


class AsyncProvider(abc.ABC):
    __slots__ = (
        "url",
        "manager",
    )

    def __init__(
        self,
        url: Optional[str] = None,
        middlewares: tuple[RequestMiddlewareType, ...] = (),
    ) -> None:
        self.url = url
        self.manager = RequestMiddlewareManager(*middlewares)

    async def __aenter__(self) -> AsyncProvider:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.close_session()

    async def __call__(
        self, method: RequestMethodType, url_or_endpoint: str = "", **kw: Any
    ) -> Response:
        middleware = self.manager.wrap_middleware(self.make_request)

        return await middleware(method=method, url_or_endpoint=url_or_endpoint, **kw)

    @abc.abstractmethod
    async def make_request(
        self, method: RequestMethodType, url_or_endpoint: str = "", **kw: Any
    ) -> Response:
        raise NotImplementedError

    @abc.abstractmethod
    async def close_session(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def stream_content(
        self,
        url_or_endpoint: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        raise_for_status: bool = True,
        **kw: Any,
    ) -> AsyncIterator[bytes]:
        yield b""

    @abc.abstractmethod
    def update_cookies(self, values: Mapping[str, Any]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def update_headers(self, values: Mapping[str, Any]) -> None:
        raise NotImplementedError
