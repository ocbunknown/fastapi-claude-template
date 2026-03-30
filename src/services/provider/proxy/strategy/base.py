from abc import ABC, abstractmethod
from typing import Callable, Unpack

from src.services.provider.proxy.types import StrategyParams


class ProxySelectionStrategy(ABC):
    @abstractmethod
    def select(
        self,
        proxies: list[str],
        count_func: Callable[[str], int],
        **params: Unpack[StrategyParams],
    ) -> str:
        raise NotImplementedError
