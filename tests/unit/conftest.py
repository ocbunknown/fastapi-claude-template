from __future__ import annotations

from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
import uuid_utils.compat as uuid

from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.jwt import JWT
from src.application.v1.services.auth import AuthService
from src.application.v1.services.gateway import ServiceGateway
from src.application.v1.usecases.auth.login import LoginUseCase
from tests.fakes import FakeHasher, FakeJWT, FakeStrCache


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        if "tests/unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


@pytest.fixture
def fake_cache() -> StrCache:
    return FakeStrCache()


@pytest.fixture
def fake_hasher() -> FakeHasher:
    return FakeHasher()


@pytest.fixture
def fake_jwt() -> JWT:
    return FakeJWT()


@pytest.fixture
def auth_service(fake_jwt: JWT, fake_cache: StrCache) -> AuthService:
    return AuthService(jwt=fake_jwt, cache=fake_cache)


@pytest.fixture
def services(auth_service: AuthService) -> ServiceGateway:
    return ServiceGateway(auth=auth_service)


@pytest.fixture
def fake_database() -> MagicMock:
    db = MagicMock()
    db.manager.session.__aenter__ = AsyncMock(return_value=None)
    db.manager.session.__aexit__ = AsyncMock(return_value=None)
    return db


@pytest.fixture
def stub_user(
    fake_database: MagicMock, fake_hasher: FakeHasher
) -> Callable[..., MagicMock]:
    def _factory(
        *,
        login: str = "alice",
        password: str = "supersecret",
        active: bool = True,
        **extra: Any,
    ) -> MagicMock:
        user = MagicMock()
        user.uuid = uuid.uuid4()
        user.login = login
        user.password = fake_hasher.hash_password(password)
        user.active = active
        for key, value in extra.items():
            setattr(user, key, value)

        fake_database.user.select = AsyncMock(
            return_value=MagicMock(result=lambda: user)
        )
        return user

    return _factory


@pytest.fixture
def login_use_case(
    fake_database: MagicMock,
    services: ServiceGateway,
    fake_hasher: FakeHasher,
) -> LoginUseCase:
    return LoginUseCase(
        database=fake_database, services=services, hasher=fake_hasher
    )
