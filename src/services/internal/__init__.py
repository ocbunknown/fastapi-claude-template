from typing import Any, Callable

from src.services.cache.redis import RedisCache
from src.services.security.jwt import JWT

from .auth import AuthService


class InternalServiceGateway:
    __slots__ = ("_cache", "_jwt", "_redis")

    def __init__(self, jwt: JWT, redis: RedisCache) -> None:
        self._redis = redis
        self._jwt = jwt
        self._cache: dict[str, Any] = {}

    @property
    def auth(self) -> AuthService:
        return self._from_cache("auth", AuthService, jwt=self._jwt, cache=self._redis)

    def _from_cache[S](self, key: str, factory: Callable[..., S], **kwargs: Any) -> S:
        if not (cached := self._cache.get(key)):
            cached = factory(**kwargs)
            self._cache[key] = cached

        return cached


__all__ = ("InternalServiceGateway",)
