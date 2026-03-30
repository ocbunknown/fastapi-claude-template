from dataclasses import dataclass, field
from typing import Any, Callable

from src.services.cache.redis import RedisCache
from src.services.security.jwt import JWT
from src.settings.core import Settings

from .external import ExternalServiceGateway
from .internal import InternalServiceGateway
from .provider.base import AsyncProvider


@dataclass(slots=True)
class ServiceFactory:
    provider: AsyncProvider
    settings: Settings
    jwt: JWT
    redis: RedisCache
    _cache: dict[str, Any] = field(default_factory=dict)

    def internal(self) -> InternalServiceGateway:
        return self._from_cache(
            "internal",
            InternalServiceGateway,
            jwt=self.jwt,
            redis=self.redis,
        )

    def external(self) -> ExternalServiceGateway:
        return self._from_cache(
            "external",
            ExternalServiceGateway,
            provider=self.provider,
            settings=self.settings,
        )

    def _from_cache[S](self, key: str, factory: Callable[..., S], **kwargs: Any) -> S:
        if not (cached := self._cache.get(key)):
            cached = factory(**kwargs)
            self._cache[key] = cached

        return cached


__all__ = (
    "ServiceFactory",
    "InternalServiceGateway",
    "ExternalServiceGateway",
)
