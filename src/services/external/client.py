from types import TracebackType
from typing import Any, Optional, Self, Unpack
from urllib.parse import urljoin

from src.services.external.request import Request
from src.services.provider.aiohttp import AiohttpProvider, ParamsType
from src.services.provider.base import AsyncProvider


class Client:
    __slots__ = ("_provider", "_url")

    def __init__(
        self,
        url: str = "",
        provider: AsyncProvider | None = None,
        *,
        proxy: str | None,
        **options: Unpack[ParamsType],
    ) -> None:
        self._provider = provider or AiohttpProvider(url, proxy, **options)
        self._url = url

    @property
    def url(self) -> str:
        return self._provider.url or self._url

    def endpoint_url(self, endpoint: str) -> str:
        return urljoin(self.url, endpoint)

    async def send[R](self, request: Request[R], /, **kwargs: Any) -> R:
        return await request(self._provider, **kwargs)

    async def __call__[R](self, request: Request[R], /, **kwargs: Any) -> R:
        return await self.send(request, **kwargs)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self._provider.__aexit__(exc_type, exc_value, traceback)
