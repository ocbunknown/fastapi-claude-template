import json
from datetime import timedelta
from typing import Any, Optional, Self, cast

from fastapi import Request as HttpRequest
from pydantic import BaseModel

from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.common.di import Depends, inject
from src.common.tools.cache import default_cache_key_builder
from src.common.tools.formatter import SafeFormatter, extract_keys_formatter


async def request_cache_key_builder(request: HttpRequest) -> str:
    query_params = {
        key: request.query_params.getlist(key) for key in request.query_params
    }

    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}

    path = request.url.path
    method = request.method
    query_key = default_cache_key_builder(query_params)
    body_key = default_cache_key_builder(body)

    return f"{path}:{method}:{query_key}:{body_key}"


def _extract_query_keys(request: HttpRequest) -> dict[str, Any]:
    query_params: dict[str, Any] = {}
    for key in request.query_params:
        values = request.query_params.getlist(key)
        query_params[key] = values[0] if len(values) == 1 else values
    return query_params


async def _extract_body_keys(request: HttpRequest) -> dict[str, Any]:
    raw_body = await request.body()
    body = json.loads(raw_body) if raw_body else {}
    return {key: body[key] for key in body.keys()}


class ResponseCache:
    def __init__(
        self,
        expires_in: timedelta = timedelta(minutes=1),
        key: str | None = None,
    ) -> None:
        self.expires_in = expires_in
        self.key = key
        self.formatter = SafeFormatter()
        self.request: Optional[HttpRequest] = None
        self._cache: Optional[StrCache] = None

    @inject
    async def __call__(self, request: HttpRequest, cache: Depends[StrCache]) -> Self:
        self.request = request
        self._cache = cache
        return self

    async def execute[Q: Request, R](self, use_case: UseCase[Q, R], message: Q, /) -> R:
        if self.request is None or self._cache is None:
            raise RuntimeError("ResponseCache must be called before execute")

        cache_key = await self._format_key(self.request, self.key)
        if not cache_key:
            cache_key = await request_cache_key_builder(self.request)

        cached: R | None = await self._get(cache_key)
        if cached is not None:
            return cached

        result: R = await use_case(message)
        if isinstance(result, BaseModel):
            await self._cache.set(
                cache_key,
                result.model_dump_json(exclude_none=True),
                expire=self.expires_in,
            )
        return result

    @inject
    async def invalidate(self, request: HttpRequest, cache: Depends[StrCache]) -> None:
        formatted_key = await self._format_key(request, self.key)
        if formatted_key:
            await cache.delete(formatted_key)

    async def _extract_request_values(self, request: HttpRequest) -> dict[str, Any]:
        body = await _extract_body_keys(request)
        return {**_extract_query_keys(request), **body}

    async def _format_key(
        self, request: HttpRequest, key: str | None = None
    ) -> str | None:
        if key is None:
            return None

        keys = extract_keys_formatter(key)
        if not keys:
            return key

        values = await self._extract_request_values(request)
        formatted_values = {k: values.get(k) for k in keys}
        return self.formatter.format(key, **formatted_values)

    async def _get[R](self, cache_key: str) -> R | None:
        if self._cache is None:
            raise RuntimeError("ResponseCache must be called before _get")
        return cast(R | None, await self._cache.get(cache_key))
