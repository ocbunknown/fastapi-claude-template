from __future__ import annotations

import typing as t

import structlog

from src.infrastructure.http.provider.middleware.base import (
    BaseRequestMiddleware,
    CallNextMiddlewareType,
)
from src.infrastructure.http.provider.response import Response
from src.infrastructure.http.provider.types import RequestMethodType


class RequestLoggingMiddleware(BaseRequestMiddleware):
    __slots__ = ("_log", "_detailed")

    def __init__(
        self,
        name: str = "app.http.client",
        detailed: bool = False,
    ) -> None:
        self._detailed = detailed
        self._log = structlog.get_logger(name)

    async def __call__(
        self,
        call_next: CallNextMiddlewareType,
        method: RequestMethodType,
        url_or_endpoint: str,
        **kw: t.Any,
    ) -> Response:
        if self._detailed:
            self._log.info(
                "outbound_request",
                method=method,
                url=url_or_endpoint,
                params=kw,
            )
        else:
            self._log.info(
                "outbound_request",
                method=method,
                url=url_or_endpoint,
            )
        return await call_next(method=method, url_or_endpoint=url_or_endpoint, **kw)
