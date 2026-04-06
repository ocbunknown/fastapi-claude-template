from collections.abc import AsyncIterator
from typing import Callable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine

from src.database.psql import DBGateway, create_database_factory
from src.database.psql.connection import (
    SessionFactoryType,
    create_sa_engine,
    create_sa_session_factory,
)
from src.database.psql.manager import TransactionManager
from src.settings.core import Settings

type DatabaseFactory = Callable[[], DBGateway]


class DatabaseProvider(Provider):
    scope = Scope.APP

    @provide
    async def engine(self, settings: Settings) -> AsyncIterator[AsyncEngine]:
        engine = create_sa_engine(
            settings.db.url,
            pool_size=settings.db.connection_pool_size,
            max_overflow=settings.db.connection_max_overflow,
            pool_pre_ping=settings.db.connection_pool_pre_ping,
        )
        try:
            yield engine
        finally:
            await engine.dispose()

    @provide
    def session_factory(self, engine: AsyncEngine) -> SessionFactoryType:
        return create_sa_session_factory(engine)

    @provide
    def database_factory(
        self, session_factory: SessionFactoryType
    ) -> DatabaseFactory:
        return create_database_factory(TransactionManager, session_factory)

    @provide(scope=Scope.REQUEST)
    def db_gateway(self, database_factory: DatabaseFactory) -> DBGateway:
        return database_factory()
