import os
from typing import (
    AsyncIterator,
    Callable,
    Final,
    Iterator,
)

import alembic.command
import pytest
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.nats import NatsContainer  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]
from testcontainers.redis import RedisContainer  # type: ignore[import-untyped]

from src.api.v1.setup import init_app_v1
from src.database import DBGateway, create_database_factory
from src.database.connection import create_sa_engine, create_sa_session_factory
from src.database.manager import TransactionManager
from src.services.cache.redis import RedisCache, get_redis
from src.services.interfaces.hasher import Hasher
from src.services.security.argon2 import get_argon2_hasher
from src.settings.core import (
    DatabaseSettings,
    NatsSettings,
    RedisSettings,
    Settings,
    load_settings,
    path,
)

pytestmark = pytest.mark.anyio

TEST_HEADERS: Final[dict[str, str]] = {
    "cf-connecting-ip": "127.0.0.1",
    "user-agent": "TestClient/1.0",
}


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def redis(redis_config: RedisSettings) -> Iterator[RedisCache]:
    yield get_redis(redis_config)


@pytest.fixture(scope="session")
def nats_config() -> Iterator[NatsSettings]:
    nats = NatsContainer()
    if os.name == "nt":
        nats.get_container_host_ip = lambda: "127.0.0.1"

    nats.with_command("-js")
    nats.start()

    with nats:
        yield NatsSettings(
            servers=[nats.nats_uri()],
            user="",
            password="",
        )


@pytest.fixture(scope="function")
async def drop_cache(redis: RedisCache) -> None:
    await redis.clear()


@pytest.fixture(scope="session")
def db_config() -> Iterator[DatabaseSettings]:
    pg = PostgresContainer()

    if os.name == "nt":
        pg.get_container_host_ip = lambda: "127.0.0.1"

    with pg:
        yield DatabaseSettings(
            uri="postgresql+asyncpg://{}:{}@{}:{}/{}",
            name=pg.dbname,
            host=pg.get_container_host_ip(),
            port=pg.get_exposed_port(pg.port),
            user=pg.username,
            password=pg.password,
        )


@pytest.fixture(scope="session")
def redis_config() -> Iterator[RedisSettings]:
    redis = RedisContainer()

    if os.name == "nt":
        redis.get_container_host_ip = lambda: "127.0.0.1"

    with redis:
        yield RedisSettings(
            host=redis.get_container_host_ip(), port=redis.get_exposed_port(redis.port)
        )


@pytest.fixture(scope="session")
def settings(
    redis_config: RedisSettings, db_config: DatabaseSettings, nats_config: NatsSettings
) -> Settings:
    return load_settings(db=db_config, redis=redis_config, nats=nats_config)


@pytest.fixture(scope="function")
async def app(settings: Settings) -> FastAPI:
    return init_app_v1(settings)


@pytest.fixture(scope="session")
def alembic_config(db_config: DatabaseSettings) -> AlembicConfig:
    cfg = AlembicConfig(path("alembic.ini"))

    cfg.set_main_option("sqlalchemy.url", db_config.url)

    return cfg


@pytest.fixture(scope="function", name="engine")
def connection_engine(
    db_config: DatabaseSettings, alembic_config: AlembicConfig
) -> Iterator[AsyncEngine]:
    engine = create_sa_engine(db_config.url)

    alembic.command.upgrade(alembic_config, "head")

    yield engine

    alembic.command.downgrade(alembic_config, "base")

    engine.sync_engine.dispose()


@pytest.fixture(scope="function")
def database_factory(engine: AsyncEngine) -> Callable[[], DBGateway]:
    session_factory = create_sa_session_factory(engine)
    database_factory = create_database_factory(TransactionManager, session_factory)
    return database_factory


@pytest.fixture(scope="function")
async def database(
    database_factory: Callable[[], DBGateway],
) -> AsyncIterator[DBGateway]:
    async with database_factory() as database:
        yield database


@pytest.fixture(scope="function")
def client(app: FastAPI, database: DBGateway) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False, headers=TEST_HEADERS) as client:
        yield client


@pytest.fixture(scope="function")
def argon() -> Hasher:
    return get_argon2_hasher()
