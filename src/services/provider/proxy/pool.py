from typing import Final, Mapping

from src.services.interfaces.pool import AsyncProxyPoolMapper, ProxyPoolMapper
from src.services.provider.proxy.datastructure.config import ProxyPoolConfig
from src.services.provider.proxy.errors import ProxyPoolEmptyError
from src.services.provider.proxy.mapper.memory import InMemoryProxyPoolMapper
from src.services.provider.proxy.strategy.base import ProxySelectionStrategy
from src.services.provider.proxy.strategy.default import (
    LeastConnectionsStrategy,
    MaxItemsPerProxyStrategy,
    RandomStrategy,
    RoundRobinStrategy,
)
from src.services.provider.proxy.types import ProxyStrategy

_STRATEGY_MAP: Final[Mapping[ProxyStrategy, type[ProxySelectionStrategy]]] = {
    "random": RandomStrategy,
    "round_robin": RoundRobinStrategy,
    "least_connections": LeastConnectionsStrategy,
    "max_items_per_proxy": MaxItemsPerProxyStrategy,
}


class ProxyPool:
    __slots__ = ("_mapper", "strategy", "max_items_per_proxy", "_strategy_class")

    @classmethod
    def from_config(
        cls,
        config: ProxyPoolConfig,
        mapper: ProxyPoolMapper[str, str] | None = None,
    ) -> "ProxyPool":
        return cls(
            proxies=config.proxies,
            strategy=config.strategy,
            max_items_per_proxy=config.max_items_per_proxy,
            mapper=mapper,
        )

    def __init__(
        self,
        proxies: list[str] | None = None,
        strategy: ProxyStrategy = "random",
        max_items_per_proxy: int | None = None,
        mapper: ProxyPoolMapper[str, str] | None = None,
    ) -> None:
        self._mapper: ProxyPoolMapper[str, str] = mapper or InMemoryProxyPoolMapper()
        self.strategy = strategy
        self.max_items_per_proxy = max_items_per_proxy
        self._strategy_class: ProxySelectionStrategy = _STRATEGY_MAP[strategy]()

        if proxies:
            self._mapper.load_proxies(proxies)

    @property
    def proxies(self) -> list[str] | None:
        return self._mapper.proxies

    def load_proxies(self, proxies: list[str]) -> None:
        self._mapper.load_proxies(proxies)

    def bind(self, proxy: str, item: str) -> None:
        self._mapper.bind(proxy, item)

    def unbind(self, proxy: str, item: str) -> bool:
        return self._mapper.unbind(proxy, item)

    def unbind_all(self, proxy: str) -> None:
        self._mapper.unbind_all(proxy)

    def remove_proxy(self, proxy: str) -> None:
        self._mapper.remove_proxy(proxy)

    def get_bound_items(self, proxy: str) -> list[str] | None:
        return self._mapper.get_bound_items(proxy)

    def count_bound_items(self, proxy: str) -> int:
        return self._mapper.count_bound_items(proxy)

    def find_proxy_for(self, item: str) -> str | None:
        return self._mapper.find_proxy_for(item)

    def get_available_proxy(self) -> str:
        if not self._mapper.proxies:
            raise ProxyPoolEmptyError()

        return self._strategy_class.select(
            self._mapper.proxies,
            self._mapper.count_bound_items,
            max_items_per_proxy=self.max_items_per_proxy,
        )

    def close(self) -> None:
        self._mapper.close()


class AsyncProxyPool:
    """Asynchronous proxy pool for managing and selecting proxies.

    This class provides two ways to create an instance:

    1. Using `from_config()` (recommended) - automatically loads proxies:
        ```python
        proxy_pool = await AsyncProxyPool.from_config(
            config=ProxyPoolConfig(
                proxies=["proxy1", "proxy2"],
                strategy="round_robin",
            ),
            mapper=redis_mapper,
        )
        # Proxies are already loaded and ready to use
        ```

    2. Using direct instantiation - requires manual proxy loading:
        ```python
        proxy_pool = AsyncProxyPool(
            mapper=redis_mapper,
            strategy="round_robin",
        )
        # Must explicitly load proxies before use
        await proxy_pool.load_proxies(["proxy1", "proxy2"])
        ```
    """

    __slots__ = ("_mapper", "strategy", "max_items_per_proxy", "_strategy_class")

    @classmethod
    async def from_config(
        cls,
        config: ProxyPoolConfig,
        mapper: AsyncProxyPoolMapper[str, str],
    ) -> "AsyncProxyPool":
        instance = cls(
            mapper=mapper,
            strategy=config.strategy,
            max_items_per_proxy=config.max_items_per_proxy,
        )

        if config.proxies:
            await instance.load_proxies(config.proxies)
        return instance

    def __init__(
        self,
        mapper: AsyncProxyPoolMapper[str, str],
        strategy: ProxyStrategy = "random",
        max_items_per_proxy: int | None = None,
    ) -> None:
        self._mapper = mapper
        self.strategy = strategy
        self.max_items_per_proxy = max_items_per_proxy
        self._strategy_class: ProxySelectionStrategy = _STRATEGY_MAP[strategy]()

    async def get_proxies(self) -> list[str]:
        return await self._mapper.proxies

    async def load_proxies(self, proxies: list[str]) -> None:
        await self._mapper.load_proxies(proxies)

    async def bind(self, proxy: str, item: str) -> None:
        await self._mapper.bind(proxy, item)

    async def unbind(self, proxy: str, item: str) -> bool:
        return await self._mapper.unbind(proxy, item)

    async def unbind_all(self, proxy: str) -> None:
        await self._mapper.unbind_all(proxy)

    async def remove_proxy(self, proxy: str) -> None:
        await self._mapper.remove_proxy(proxy)

    async def get_bound_items(self, proxy: str) -> list[str] | None:
        return await self._mapper.get_bound_items(proxy)

    async def count_bound_items(self, proxy: str) -> int:
        return await self._mapper.count_bound_items(proxy)

    async def find_proxy_for(self, item: str) -> str | None:
        return await self._mapper.find_proxy_for(item)

    async def get_available_proxy(self) -> str:
        proxies_with_counts = await self._mapper.get_proxies_with_counts()

        if not proxies_with_counts:
            raise ProxyPoolEmptyError()

        proxies_list = list(proxies_with_counts.keys())
        return self._strategy_class.select(
            proxies_list,
            lambda p: proxies_with_counts[p],
            max_items_per_proxy=self.max_items_per_proxy,
        )

    async def close(self) -> None:
        await self._mapper.close()
