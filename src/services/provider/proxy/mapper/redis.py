from typing import Any, Final

import redis.asyncio as aioredis

_GET_PROXIES_WITH_COUNTS_SCRIPT: Final[str] = """
local proxies_key = KEYS[1]
local key_prefix = ARGV[1]

local proxies = redis.call('SMEMBERS', proxies_key)
local result = {}

for _, proxy in ipairs(proxies) do
    local proxy_key = key_prefix .. ':proxy:' .. proxy
    local count = redis.call('SCARD', proxy_key)

    table.insert(result, proxy)
    table.insert(result, tostring(count))
end

return result
"""


class RedisProxyPoolMapper:
    __slots__ = (
        "_redis",
        "_key_prefix",
        "_proxies_key",
        "_get_available_script",
    )

    def __init__(
        self,
        redis: aioredis.Redis,  # type: ignore[type-arg]
        key_prefix: str = "proxy_pool",
    ) -> None:
        self._redis = redis
        self._key_prefix = key_prefix
        self._proxies_key = f"{key_prefix}:proxies"
        self._get_available_script: Any = None

    @property
    async def proxies(self) -> list[str]:
        members = await self._redis.smembers(self._proxies_key)
        return list(members) if members else []

    def _get_proxy_key(self, proxy: str) -> str:
        return f"{self._key_prefix}:proxy:{proxy}"

    async def load_proxies(self, proxies: list[str]) -> None:
        if proxies:
            await self._redis.sadd(self._proxies_key, *proxies)

    async def bind(self, proxy: str, item: str) -> None:
        lock_key = f"{self._key_prefix}:bind:{proxy}"
        async with self._redis.lock(lock_key, timeout=5.0, blocking_timeout=3.0):
            async with self._redis.pipeline() as pipe:
                await pipe.sadd(self._proxies_key, proxy)
                await pipe.sadd(self._get_proxy_key(proxy), item)
                await pipe.execute()

    async def unbind(self, proxy: str, item: str) -> bool:
        lock_key = f"{self._key_prefix}:bind:{proxy}"
        async with self._redis.lock(lock_key, timeout=5.0, blocking_timeout=3.0):
            result = await self._redis.srem(self._get_proxy_key(proxy), item)
            return bool(result)

    async def unbind_all(self, proxy: str) -> None:
        await self._redis.delete(self._get_proxy_key(proxy))

    async def remove_proxy(self, proxy: str) -> None:
        async with self._redis.pipeline() as pipe:
            await pipe.srem(self._proxies_key, proxy)
            await pipe.delete(self._get_proxy_key(proxy))
            await pipe.execute()

    async def get_bound_items(self, proxy: str) -> list[str] | None:
        members = await self._redis.smembers(self._get_proxy_key(proxy))
        return list(members) if members else None

    async def count_bound_items(self, proxy: str) -> int:
        return await self._redis.scard(self._get_proxy_key(proxy))

    async def find_proxy_for(self, item: str) -> str | None:
        proxies = await self.proxies

        if not proxies:
            return None

        for proxy in proxies:
            is_member = await self._redis.sismember(self._get_proxy_key(proxy), item)
            if is_member:
                return proxy

        return None

    async def get_proxies_with_counts(self) -> dict[str, int]:
        if self._get_available_script is None:
            self._get_available_script = self._redis.register_script(
                _GET_PROXIES_WITH_COUNTS_SCRIPT
            )

        result = await self._get_available_script(
            keys=[self._proxies_key],
            args=[self._key_prefix],
        )

        if not result:
            return {}

        return {result[i]: int(result[i + 1]) for i in range(0, len(result), 2)}

    async def close(self) -> None:
        """Clean up all proxy-related keys including the proxies set."""
        pattern = f"{self._key_prefix}:proxy:*"
        keys_to_delete = []

        async for key in self._redis.scan_iter(pattern):
            keys_to_delete.append(key)

        async with self._redis.pipeline() as pipe:
            if keys_to_delete:
                for key in keys_to_delete:
                    await pipe.delete(key)
            await pipe.delete(self._proxies_key)
            await pipe.execute()
