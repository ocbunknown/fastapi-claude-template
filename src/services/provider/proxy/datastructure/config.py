from dataclasses import dataclass

from src.services.provider.proxy.types import ProxyStrategy


@dataclass
class ProxyPoolConfig:
    proxies: list[str] | None = None
    strategy: ProxyStrategy = "random"
    max_items_per_proxy: int | None = None
