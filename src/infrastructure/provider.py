from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.hasher import Hasher
from src.application.common.interfaces.jwt import JWT as JWTProtocol
from src.infrastructure.cache import get_redis
from src.infrastructure.http.provider.aiohttp import AiohttpProvider
from src.infrastructure.security import JWT, get_argon2_hasher
from src.settings.core import Settings


class InfrastructureProvider(Provider):
    scope = Scope.APP

    @provide
    async def cache(self, settings: Settings) -> AsyncIterator[StrCache]:
        redis = get_redis(settings.redis)
        try:
            yield redis
        finally:
            await redis.close()

    @provide
    async def aiohttp_provider(self) -> AsyncIterator[AiohttpProvider]:
        provider = AiohttpProvider()
        try:
            yield provider
        finally:
            await provider.close_session()

    @provide
    def jwt(self, settings: Settings) -> JWTProtocol:
        return JWT(settings.ciphers)

    @provide
    def hasher(self) -> Hasher:
        return get_argon2_hasher()
