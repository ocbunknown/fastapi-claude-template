from dishka import Provider, Scope
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.common.interfaces.mediator import Mediator
from src.api.common.mediator import MediatorImpl
from src.api.v1.handlers import setup_handlers
from src.common.di import container
from src.common.tools.singleton import singleton
from src.database import DBGateway, create_database_factory
from src.database.connection import create_sa_engine, create_sa_session_factory
from src.database.manager import TransactionManager
from src.services import ServiceFactory
from src.services.cache.redis import RedisCache, get_redis
from src.services.external import ExternalServiceGateway
from src.services.interfaces.hasher import Hasher
from src.services.internal import InternalServiceGateway
from src.services.provider.aiohttp import AiohttpProvider
from src.services.security.argon2 import get_argon2_hasher
from src.services.security.jwt import JWT
from src.settings.core import Settings


def setup_dependencies(app: FastAPI, settings: Settings) -> None:
    redis = get_redis(settings.redis)

    engine = create_sa_engine(
        settings.db.url,
        pool_size=settings.db.connection_pool_size,
        max_overflow=settings.db.connection_max_overflow,
        pool_pre_ping=settings.db.connection_pool_pre_ping,
    )

    session_factory = create_sa_session_factory(engine)
    database_factory = create_database_factory(TransactionManager, session_factory)

    hasher = get_argon2_hasher()
    jwt = JWT(settings.ciphers)

    aiohttp_provider = AiohttpProvider()
    service_factory = ServiceFactory(
        provider=aiohttp_provider,
        settings=settings,
        jwt=jwt,
        redis=redis,
    )

    mediator = (
        MediatorImpl.builder()
        .dependencies(
            hasher=hasher,
            redis=redis,
            jwt=jwt,
            settings=settings,
            database=database_factory,
            external_gateway=service_factory.external(),
            internal_gateway=service_factory.internal(),
        )
        .handlers(setup_handlers)
        .middleware()
        .build()
    )

    provider = Provider(scope=Scope.APP)

    provider.provide(singleton(mediator), provides=Mediator)
    provider.provide(singleton(settings), provides=Settings)
    provider.provide(singleton(redis), provides=RedisCache)
    provider.provide(singleton(engine), provides=AsyncEngine)
    provider.provide(singleton(aiohttp_provider), provides=AiohttpProvider)
    provider.provide(singleton(jwt), provides=JWT)
    provider.provide(singleton(hasher), provides=Hasher)
    provider.provide(database_factory, provides=DBGateway, scope=Scope.REQUEST)
    provider.provide(service_factory.internal, provides=InternalServiceGateway)
    provider.provide(service_factory.external, provides=ExternalServiceGateway)

    container.add_providers(provider, FastapiProvider())

    setup_dishka(container.get_container(), app)
