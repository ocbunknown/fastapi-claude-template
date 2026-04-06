from __future__ import annotations

from typing import Callable
from unittest.mock import MagicMock

import pytest

from src.application.common.exceptions import ForbiddenError, UnAuthorizedError
from src.application.v1.usecases.auth.login import LoginRequest, LoginUseCase


async def test_login_returns_tokens(
    login_use_case: LoginUseCase, stub_user: Callable[..., MagicMock]
) -> None:
    stub_user(password="supersecret")

    result = await login_use_case(
        LoginRequest(login="alice", password="supersecret", fingerprint="fp-1")
    )

    assert result.tokens.access
    assert result.tokens.refresh


async def test_login_wrong_password_raises_unauthorized(
    login_use_case: LoginUseCase, stub_user: Callable[..., MagicMock]
) -> None:
    stub_user(password="real-password-here")

    with pytest.raises(UnAuthorizedError):
        await login_use_case(
            LoginRequest(
                login="alice", password="wrongpassword", fingerprint="fp-1"
            )
        )


async def test_login_blocked_user_raises_forbidden(
    login_use_case: LoginUseCase, stub_user: Callable[..., MagicMock]
) -> None:
    stub_user(password="supersecret", active=False)

    with pytest.raises(ForbiddenError):
        await login_use_case(
            LoginRequest(
                login="alice", password="supersecret", fingerprint="fp-1"
            )
        )
