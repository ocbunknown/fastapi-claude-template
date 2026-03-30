from collections import defaultdict


class InMemoryProxyPoolMapper[K, V]:
    __slots__ = ("_proxies", "proxy_map")

    def __init__(self) -> None:
        self._proxies: list[K] = []
        self.proxy_map: defaultdict[K, list[V]] = defaultdict(list)

    @property
    def proxies(self) -> list[K]:
        return self._proxies

    def load_proxies(self, proxies: list[K]) -> None:
        self._proxies = proxies

    def bind(self, proxy: K, item: V) -> None:
        self.proxy_map[proxy].append(item)

    def unbind(self, proxy: K, item: V) -> bool:
        if proxy in self.proxy_map and item in self.proxy_map[proxy]:
            self.proxy_map[proxy].remove(item)
            return True
        return False

    def unbind_all(self, proxy: K) -> None:
        if proxy in self.proxy_map:
            self.proxy_map[proxy].clear()

    def remove_proxy(self, proxy: K) -> None:
        if self._proxies and proxy in self._proxies:
            self._proxies.remove(proxy)
        if proxy in self.proxy_map:
            del self.proxy_map[proxy]

    def get_bound_items(self, proxy: K) -> list[V] | None:
        return self.proxy_map.get(proxy)

    def count_bound_items(self, proxy: K) -> int:
        return len(self.proxy_map[proxy])

    def find_proxy_for(self, item: V) -> K | None:
        return next(
            (proxy for proxy, items in self.proxy_map.items() if item in items),
            None,
        )

    def close(self) -> None:
        self._proxies.clear()
        self.proxy_map.clear()
