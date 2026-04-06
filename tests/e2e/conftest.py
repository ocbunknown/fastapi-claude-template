from __future__ import annotations

from typing import AsyncIterator

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.application.common.interfaces.hasher import Hasher
from src.application.provider import ApplicationProvider
from src.database.psql import DBGateway, create_database_factory
from src.database.psql.connection import SessionFactoryType
from src.database.psql.manager import TransactionManager
from src.database.psql.provider import DatabaseFactory
from src.infrastructure.broker.provider import BrokerProvider
from src.infrastructure.provider import InfrastructureProvider
from src.presentation.http.common.exception_handlers import (
    setup_exception_handlers,
)
from src.presentation.http.common.middlewares import setup_global_middlewares
from src.presentation.http.common.responses import ORJSONResponse
from src.presentation.http.v1.endpoints import setup_v1_routers
from src.settings.core import Settings
from src.settings.provider import SettingsProvider


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        if "tests/e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


class _TestDatabaseProvider(Provider):
    scope = Scope.APP

    def __init__(self, test_factory: async_sessionmaker) -> None:  # type: ignore[type-arg]
        super().__init__()
        self._test_factory = test_factory

    @provide
    def session_factory(self) -> SessionFactoryType:
        return self._test_factory

    @provide
    def database_factory(self, session_factory: SessionFactoryType) -> DatabaseFactory:
        return create_database_factory(TransactionManager, session_factory)

    @provide(scope=Scope.REQUEST)
    def db_gateway(self, database_factory: DatabaseFactory) -> DBGateway:
        return database_factory()


@pytest.fixture
async def e2e_app(
    settings: Settings,
    test_session_factory: async_sessionmaker,  # type: ignore[type-arg]
) -> AsyncIterator[FastAPI]:
    container = make_async_container(
        SettingsProvider(),
        InfrastructureProvider(),
        _TestDatabaseProvider(test_session_factory),
        BrokerProvider(),
        ApplicationProvider(),
        FastapiProvider(),
        context={Settings: settings},
    )

    app = FastAPI(default_response_class=ORJSONResponse)
    setup_dishka(container, app)
    setup_v1_routers(app)
    setup_exception_handlers(app)
    setup_global_middlewares(app, settings.server)

    try:
        yield app
    finally:
        await container.close()


@pytest.fixture
async def client(e2e_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """httpx.AsyncClient + ASGITransport runs the app in the same event loop
    as the test, avoiding the asyncpg "attached to a different loop" issue
    that ``TestClient`` triggers via its anyio portal bridging."""
    transport = httpx.ASGITransport(app=e2e_app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as test_client:
        yield test_client


@pytest.fixture
async def hasher(e2e_app: FastAPI) -> Hasher:
    """Resolve the real Argon2 hasher from the e2e container so seeded
    passwords match what the login use case expects."""
    container = e2e_app.state.dishka_container
    instance: Hasher = await container.get(Hasher)
    return instance


@pytest.fixture
async def admin_credentials(database: DBGateway, hasher: Hasher) -> tuple[str, str]:
    """Seed an Admin-role user directly via the DBGateway and return its
    plaintext credentials. Bypasses the register/confirm flow because that
    requires an out-of-band verification code."""
    login = "admin-e2e"
    password = "supersecret"

    async with database:
        role = (await database.role.select(name="Admin")).result()
        await database.user.create(
            login=login,
            password=hasher.hash_password(password),
            role_uuid=role.uuid,
        )

    return login, password


@pytest.fixture
async def admin_token(
    client: httpx.AsyncClient, admin_credentials: tuple[str, str]
) -> str:
    """Log in as the seeded admin and return the bearer access token."""
    login, password = admin_credentials
    response = await client.post(
        "/v1/auth/login",
        json={"login": login, "password": password, "fingerprint": "e2e-fp"},
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["token"]
    return token
