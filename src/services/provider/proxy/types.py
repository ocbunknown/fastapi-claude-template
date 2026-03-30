from typing import Literal, TypedDict

type ProxyStrategy = Literal[
    "random", "round_robin", "least_connections", "max_items_per_proxy"
]


class StrategyParams(TypedDict, total=False):
    max_items_per_proxy: int | None
