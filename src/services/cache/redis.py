from datetime import timedelta
from typing import Any

import redis.asyncio as aioredis

from src.settings.core import RedisSettings


class RedisCache:
    __slots__ = ("_redis",)

    def __init__(self, redis: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis

    async def get(
        self,
        key: str,
    ) -> str | None:
        return await self._redis.get(key)

    async def set(
        self, key: str, value: Any, expire: float | timedelta | None = None, **kw: Any
    ) -> None:
        await self._redis.set(key, value, ex=expire, **kw)

    async def delete(self, *keys: str) -> None:
        found_keys = [
            found for key in keys async for found in self._redis.scan_iter(key)
        ]
        if found_keys:
            await self._redis.delete(*found_keys)

    async def set_list(
        self, key: str, *values: Any, expire: float | timedelta | None = None, **kw: Any
    ) -> None:
        await self._redis.lpush(key, *(v for v in values))

        if expire:
            await self._redis.expire(
                key,
                expire if isinstance(expire, timedelta) else timedelta(seconds=expire),
                **kw,
            )

    async def get_list(
        self,
        key: str,
        **kw: Any,
    ) -> list[str]:
        start, end = kw.pop("start", 0), kw.pop("end", -1)
        return await self._redis.lrange(key, start, end)

    async def discard(
        self,
        key: str,
        value: Any,
        **kw: Any,
    ) -> None:
        count = kw.pop("count", 0)
        await self._redis.lrem(key, count, value)

    async def clear(self) -> None:
        await self._redis.flushall(asynchronous=True)

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.keys(key))

    async def keys(self) -> list[str]:
        return await self._redis.keys("*")

    async def close(self) -> None:
        await self._redis.aclose(close_connection_pool=True)  # type: ignore


def get_redis(settings: RedisSettings, **kw: Any) -> RedisCache:
    return RedisCache(
        aioredis.Redis(
            host=settings.host,
            port=settings.port,
            password=settings.password,
            decode_responses=True,
            **kw,
        )
    )
