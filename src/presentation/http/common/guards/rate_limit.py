from datetime import timedelta
from time import time
from typing import Literal

import orjson
from fastapi import Request

from src.application.common.exceptions import TooManyRequestsError
from src.application.common.interfaces.cache import StrCache
from src.common.di import Depends, inject

type DurationUnit = Literal["second", "minute", "hour", "day"]
DURATION_VALUES: dict[DurationUnit, timedelta] = {
    "second": timedelta(seconds=1),
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
}


class RateLimit:
    __slots__ = (
        "duration",
        "limit",
        "scope",
        "header_policy",
        "header_limit",
        "header_remaining",
        "header_reset",
    )

    def __init__(
        self,
        *,
        unit: DurationUnit,
        limit: int,
        scope: str | None = None,
        header_policy: str = "RateLimit-Policy",
        header_limit: str = "RateLimit-Limit",
        header_remaining: str = "RateLimit-Remaining",
        header_reset: str = "RateLimit-Reset",
    ) -> None:
        self.duration = DURATION_VALUES[unit]
        self.limit = limit
        self.scope = scope
        self.header_policy = header_policy
        self.header_limit = header_limit
        self.header_remaining = header_remaining
        self.header_reset = header_reset

    @inject
    async def __call__(
        self, request: Request, store: Depends[StrCache]
    ) -> None:
        ip = self._get_client_ip(request)
        scope = self.scope or f"{request.method}:{request.url.path}"
        key = f"ratelimit::{ip}::{scope}"
        now = int(time())
        window = int(self.duration.total_seconds())

        history, reset_ts = await self._get_history(store, key, now, window)
        history = self._prune_history(history, now, window)

        if len(history) >= self.limit:
            retry_after = reset_ts - now
            raise TooManyRequestsError(
                message="Too Many Requests",
                headers=self._build_headers(
                    remaining=0, retry_after=retry_after
                ),
            )

        history.insert(0, now)
        await self._save_history(store, key, history, reset_ts)

        remaining = self.limit - len(history)
        request.state.rate_limit_headers = self._build_headers(
            remaining=remaining, retry_after=reset_ts - now
        )

    def _get_client_ip(self, request: Request) -> str:
        if forwarded := request.headers.get("X-Forwarded-For"):
            return forwarded.split(",")[0].strip()
        if real_ip := request.headers.get("X-Real-IP"):
            return real_ip
        return request.client.host if request.client else "anonymous"

    async def _get_history(
        self, store: StrCache, key: str, now: int, window: int
    ) -> tuple[list[int], int]:
        raw = await store.get(key)
        if not raw:
            return [], now + window

        data = orjson.loads(raw)
        history: list[int] = data.get("history", [])
        reset_ts = int(data.get("reset", now + window))
        if now >= reset_ts:
            return [], now + window
        return history, reset_ts

    def _prune_history(
        self, history: list[int], now: int, window: int
    ) -> list[int]:
        cutoff = now - window
        return [ts for ts in history if ts > cutoff]

    async def _save_history(
        self,
        store: StrCache,
        key: str,
        history: list[int],
        reset_ts: int,
    ) -> None:
        payload = orjson.dumps({"history": history, "reset": reset_ts})
        await store.set(key, payload, expire=self.duration)

    def _build_headers(
        self, remaining: int, retry_after: int | None = None
    ) -> dict[str, str]:
        window = int(self.duration.total_seconds())
        headers: dict[str, str] = {
            self.header_policy: f"{self.limit}; w={window}",
            self.header_limit: str(self.limit),
            self.header_remaining: str(remaining),
        }
        if retry_after is not None:
            headers[self.header_reset] = str(retry_after)
        return headers
