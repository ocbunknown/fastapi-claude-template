import abc
import typing as t

from src.services.provider.response import Response
from src.services.provider.types import RequestMethodType


class CallNextMiddlewareType(t.Protocol):
    async def __call__(
        self, method: RequestMethodType, url_or_endpoint: str, **kw: t.Any
    ) -> Response: ...


class RequestMiddlewareType(t.Protocol):
    async def __call__(
        self,
        call_next: CallNextMiddlewareType,
        method: RequestMethodType,
        url_or_endpoint: str,
        **kw: t.Any,
    ) -> Response: ...


class BaseRequestMiddleware(abc.ABC):
    @abc.abstractmethod
    async def __call__(
        self,
        call_next: CallNextMiddlewareType,
        method: RequestMethodType,
        url_or_endpoint: str,
        **kw: t.Any,
    ) -> Response:
        raise NotImplementedError
