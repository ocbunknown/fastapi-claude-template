import random
from typing import Callable, Unpack

from src.services.provider.proxy.errors import ProxyPoolEmptyError, ProxyPoolFullError
from src.services.provider.proxy.strategy.base import ProxySelectionStrategy
from src.services.provider.proxy.types import StrategyParams


class RandomStrategy(ProxySelectionStrategy):
    def select(
        self,
        proxies: list[str],
        count_func: Callable[[str], int],
        **params: Unpack[StrategyParams],
    ) -> str:
        if not proxies:
            raise ProxyPoolEmptyError()
        return random.choice(proxies)


class RoundRobinStrategy(ProxySelectionStrategy):
    __slots__ = ("_current_index",)

    def __init__(self) -> None:
        self._current_index = 0

    def select(
        self,
        proxies: list[str],
        count_func: Callable[[str], int],
        **params: Unpack[StrategyParams],
    ) -> str:
        if not proxies:
            raise ProxyPoolEmptyError()

        proxy = proxies[self._current_index % len(proxies)]
        self._current_index += 1
        return proxy


class LeastConnectionsStrategy(ProxySelectionStrategy):
    def select(
        self,
        proxies: list[str],
        count_func: Callable[[str], int],
        **params: Unpack[StrategyParams],
    ) -> str:
        if not proxies:
            raise ProxyPoolEmptyError()
        return min(proxies, key=count_func)


class MaxItemsPerProxyStrategy(ProxySelectionStrategy):
    def select(
        self,
        proxies: list[str],
        count_func: Callable[[str], int],
        **params: Unpack[StrategyParams],
    ) -> str:
        if not proxies:
            raise ProxyPoolEmptyError()

        max_items = params.get("max_items_per_proxy")

        if max_items is None:
            return max(proxies, key=count_func)

        available = [p for p in proxies if count_func(p) < max_items]
        if not available:
            raise ProxyPoolFullError()

        return max(available, key=count_func)
