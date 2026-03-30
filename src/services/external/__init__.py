from typing import Any, Callable

from src.services.provider.base import AsyncProvider
from src.settings.core import Settings


class ExternalServiceGateway:
    __slots__ = ("provider", "settings", "_cache")

    def __init__(self, provider: AsyncProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings
        self._cache: dict[str, Any] = {}

    def _from_cache[S](self, key: str, factory: Callable[..., S], **kwargs: Any) -> S:
        if not (cached := self._cache.get(key)):
            cached = factory(self.provider, **kwargs)
            self._cache[key] = cached

        return cached
