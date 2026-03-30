from __future__ import annotations

import logging
import typing as t

from src.services.provider.middleware.base import (
    BaseRequestMiddleware,
    CallNextMiddlewareType,
)
from src.services.provider.response import Response
from src.services.provider.types import RequestMethodType


class RequestLoggingMiddleware(BaseRequestMiddleware):
    __slots__ = (
        "logger",
        "detailed",
    )

    def __init__(
        self,
        name: str = "LOG",
        level: logging._Level = "INFO",
        detailed: bool = False,
        custom_logger: t.Optional[logging.Logger] = None,
    ) -> None:
        self.detailed = detailed
        self.logger = custom_logger or self._setup_logger(name=name, level=level)

    def _setup_logger(self, name: str, level: logging._Level) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(logging.StreamHandler())

        return logger

    async def __call__(
        self,
        call_next: CallNextMiddlewareType,
        method: RequestMethodType,
        url_or_endpoint: str,
        **kw: t.Any,
    ) -> Response:
        if not self.detailed:
            msg = f"Making request with method: {method}, url: {url_or_endpoint}"
        else:
            msg = f"Making request with:\nMethod: {method}\nUrl: {url_or_endpoint}\nParams: {kw}"

        self.logger.info(msg)

        return await call_next(method=method, url_or_endpoint=url_or_endpoint, **kw)
