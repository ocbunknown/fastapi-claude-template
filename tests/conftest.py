from __future__ import annotations

import os
from typing import AsyncIterator, Callable, Iterator

import alembic.command
import psycopg2  # type: ignore[import-untyped]
import pytest
import uuid_utils.compat as uuid
from alembic.config import Config as AlembicConfig
from psycopg2.extensions import (  # type: ignore[import-untyped]
    ISOLATION_LEVEL_AUTOCOMMIT,
)
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from testcontainers.nats import NatsContainer  # type: ignore[import-untyped]
from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]
from testcontainers.redis import RedisContainer  # type: ignore[import-untyped]

from src.database.psql import DBGateway
from src.database.psql.connection import create_sa_engine
from src.database.psql.manager import TransactionManager
from src.settings.core import (
    CipherSettings,
    DatabaseSettings,
    NatsSettings,
    RedisSettings,
    Settings,
    load_settings,
    path,
)


@pytest.fixture(scope="session")
def worker_id(request: pytest.FixtureRequest) -> str:
    workerinput = getattr(request.config, "workerinput", None)
    if workerinput is None:
        return "master"
    return str(workerinput.get("workerid", "master"))


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    pg = PostgresContainer("postgres:16-alpine")
    if os.name == "nt":
        pg.get_container_host_ip = lambda: "127.0.0.1"
    with pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    redis = RedisContainer("redis:7-alpine")
    if os.name == "nt":
        redis.get_container_host_ip = lambda: "127.0.0.1"
    with redis:
        yield redis


@pytest.fixture(scope="session")
def nats_container() -> Iterator[NatsContainer]:
    nats = NatsContainer()
    if os.name == "nt":
        nats.get_container_host_ip = lambda: "127.0.0.1"
    nats.with_command("-js")
    with nats:
        yield nats


@pytest.fixture(scope="session")
def _worker_database(
    postgres_container: PostgresContainer, worker_id: str
) -> Iterator[str]:
    db_name = f"test_{worker_id}"
    admin_dsn = (
        f"postgresql://{postgres_container.username}:{postgres_container.password}"
        f"@{postgres_container.get_container_host_ip()}"
        f":{postgres_container.get_exposed_port(postgres_container.port)}"
        f"/{postgres_container.dbname}"
    )

    conn = psycopg2.connect(admin_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            cur.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        conn.close()

    yield db_name

    conn = psycopg2.connect(admin_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    finally:
        conn.close()


@pytest.fixture(scope="session")
def db_settings(
    postgres_container: PostgresContainer, _worker_database: str
) -> DatabaseSettings:
    return DatabaseSettings(
        uri="postgresql+asyncpg://{}:{}@{}:{}/{}",
        name=_worker_database,
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(postgres_container.port)),
        user=postgres_container.username,
        password=postgres_container.password,
    )


@pytest.fixture(scope="session")
def redis_settings(redis_container: RedisContainer) -> RedisSettings:
    return RedisSettings(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(redis_container.port)),
    )


@pytest.fixture(scope="session")
def nats_settings(nats_container: NatsContainer) -> NatsSettings:
    return NatsSettings(servers=[nats_container.nats_uri()], user="", password="")


@pytest.fixture(scope="session")
def cipher_settings() -> CipherSettings:
    """Real-shaped cipher settings for tests so JWT issuance and verification
    work end-to-end.

    The repo's default ``CipherSettings`` ships with zero token TTLs and an
    empty secret, which would make ``JWT.create`` raise on any login. We
    inject a minimal but valid HS256 setup just for tests. For HS256 (a
    symmetric algorithm) ``secret_key`` and ``public_key`` must hold the
    same key — ``JWT.verify_token`` decodes with ``public_key``."""
    import base64
    import secrets

    key = base64.b64encode(secrets.token_bytes(32)).decode()
    return CipherSettings(
        algorithm="HS256",
        secret_key=key,
        public_key=key,
        access_token_expire_seconds=3600,
        refresh_token_expire_seconds=86400,
    )


@pytest.fixture(scope="session")
def settings(
    db_settings: DatabaseSettings,
    redis_settings: RedisSettings,
    nats_settings: NatsSettings,
    cipher_settings: CipherSettings,
) -> Settings:
    return load_settings(
        db=db_settings,
        redis=redis_settings,
        nats=nats_settings,
        ciphers=cipher_settings,
    )


@pytest.fixture(scope="session")
def alembic_config(db_settings: DatabaseSettings) -> AlembicConfig:
    cfg = AlembicConfig(path("alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_settings.url)
    return cfg


@pytest.fixture(scope="session")
def _migrate_database(
    alembic_config: AlembicConfig, db_settings: DatabaseSettings
) -> None:
    """Run migrations in a sync context, before any pytest-asyncio loop is
    started. ``migrations/env.py`` invokes ``asyncio.run`` internally, which
    explodes if it ends up nested inside an already-running event loop —
    that happens when the call lives inside an ``async def`` fixture."""
    alembic.command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
async def db_engine(
    db_settings: DatabaseSettings,
    _migrate_database: None,
) -> AsyncIterator[AsyncEngine]:
    engine = create_sa_engine(
        db_settings.url,
        pool_size=2,
        max_overflow=4,
        pool_pre_ping=False,
    )

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_connection(
    db_engine: AsyncEngine,
) -> AsyncIterator[AsyncConnection]:
    """Open one connection per test, wrapped in an outer transaction that is
    rolled back at teardown. The session bound to this connection uses
    ``join_transaction_mode="create_savepoint"`` (see ``test_session_factory``)
    so each ``session.commit()`` releases a savepoint inside the outer
    transaction — SQLAlchemy 2.0 handles savepoint restart automatically, no
    manual ``after_transaction_end`` listener needed."""
    async with db_engine.connect() as connection:
        outer_tx = await connection.begin()
        try:
            yield connection
        finally:
            if outer_tx.is_active:
                await outer_tx.rollback()


@pytest.fixture
def test_session_factory(
    db_connection: AsyncConnection,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )


@pytest.fixture
async def db_session(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    session = test_session_factory()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
def database(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> DBGateway:
    return DBGateway(TransactionManager(test_session_factory()))


@pytest.fixture
def unique_login() -> Callable[[], str]:
    def _factory() -> str:
        return f"user-{uuid.uuid4().hex[:8]}"

    return _factory
