from __future__ import annotations

import uuid_utils.compat as uuid

from src.application.common.interfaces.cache import StrCache
from src.application.v1.services.auth import (
    DEFAULT_TOKENS_COUNT,
    AuthService,
)


async def test_login_creates_token_pair(auth_service: AuthService) -> None:
    user_uuid = uuid.uuid4()

    result = await auth_service.login("fp-1", user_uuid)

    assert result.tokens.access
    assert result.tokens.refresh
    assert result.tokens.access != result.tokens.refresh


async def test_login_persists_refresh_in_cache(
    auth_service: AuthService, fake_cache: StrCache
) -> None:
    user_uuid = uuid.uuid4()

    result = await auth_service.login("fp-1", user_uuid)

    cached = await fake_cache.get_list(str(user_uuid))
    assert len(cached) == 1
    assert f"fp-1::{result.tokens.refresh}" in cached


async def test_login_evicts_when_token_count_exceeded(
    auth_service: AuthService, fake_cache: StrCache
) -> None:
    user_uuid = uuid.uuid4()

    for i in range(DEFAULT_TOKENS_COUNT + 2):
        await fake_cache.set_list(str(user_uuid), f"fp-{i}::token-{i}")

    await auth_service.login("fp-new", user_uuid)

    cached = await fake_cache.get_list(str(user_uuid))
    assert len(cached) == 1
    assert "fp-new::" in cached[0]


async def test_verify_token_returns_user_uuid(auth_service: AuthService) -> None:
    user_uuid = uuid.uuid4()
    result = await auth_service.login("fp-1", user_uuid)

    parsed = await auth_service.verify_token(result.tokens.access, "access")

    assert parsed == user_uuid
