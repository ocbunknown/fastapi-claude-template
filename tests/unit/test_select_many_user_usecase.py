from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import uuid_utils.compat as uuid

from src.application.common.pagination import OffsetPagination
from src.application.v1.usecases.user.select_many import (
    SelectManyUserRequest,
    SelectManyUserUseCase,
)


def _make_orm_user(login: str = "alice") -> MagicMock:
    """Stub an ORM ``User`` whose ``as_dict()`` returns only the columns
    that would actually be populated by a ``SELECT`` without eager-loaded
    relationships — mirroring what ``Base.as_dict()`` produces in production
    (it iterates ``__dict__``, which omits unloaded relations)."""
    user = MagicMock()
    user.uuid = uuid.uuid4()
    user.login = login
    user.active = True
    user.as_dict.return_value = {
        "uuid": user.uuid,
        "login": login,
        "active": True,
    }
    return user


@pytest.fixture
def select_many_repo_call(fake_database: MagicMock) -> Any:
    """Stub database.user.select_many to return a fixed (total, users) tuple
    and capture the kwargs it was called with."""

    captured: dict[str, Any] = {}

    def _stub(total: int, users: list[Any]) -> None:
        async def _select_many(*loads: Any, **kwargs: Any) -> MagicMock:
            captured["loads"] = loads
            captured["kwargs"] = kwargs
            return MagicMock(result=lambda: (total, users))

        fake_database.user.select_many = AsyncMock(side_effect=_select_many)

    _stub.captured = captured  # type: ignore[attr-defined]
    return _stub


@pytest.fixture
def use_case(fake_database: MagicMock) -> SelectManyUserUseCase:
    return SelectManyUserUseCase(database=fake_database)


async def test_returns_offset_result_with_metadata(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    select_many_repo_call(
        total=42, users=[_make_orm_user("alice"), _make_orm_user("bob")]
    )

    result = await use_case(
        SelectManyUserRequest(
            pagination=OffsetPagination(offset=20, limit=50, order_by="asc")
        )
    )

    assert result.total == 42
    assert result.offset == 20
    assert result.limit == 50
    assert len(result.data) == 2
    assert [u.login for u in result.data] == ["alice", "bob"]


async def test_passes_pagination_kwargs_to_repository(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    select_many_repo_call(total=0, users=[])

    await use_case(
        SelectManyUserRequest(
            pagination=OffsetPagination(offset=100, limit=25, order_by="asc")
        )
    )

    kwargs = select_many_repo_call.captured["kwargs"]
    assert kwargs["offset"] == 100
    assert kwargs["limit"] == 25
    assert kwargs["order_by"] == "asc"


async def test_propagates_filters_to_repository(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    select_many_repo_call(total=0, users=[])
    role_uuid = uuid.uuid4()

    await use_case(SelectManyUserRequest(login="alice", role_uuid=role_uuid))

    kwargs = select_many_repo_call.captured["kwargs"]
    assert kwargs["login"] == "alice"
    assert kwargs["role_uuid"] == role_uuid


async def test_passes_loads_as_positional_args(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    select_many_repo_call(total=0, users=[])

    await use_case(SelectManyUserRequest(loads=("role",)))

    assert select_many_repo_call.captured["loads"] == ("role",)


async def test_unlimited_pagination_passes_none_to_repository(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    """Internal callers can request all rows by leaving limit as None."""
    select_many_repo_call(total=0, users=[])

    await use_case(SelectManyUserRequest(pagination=OffsetPagination(limit=None)))

    assert select_many_repo_call.captured["kwargs"]["limit"] is None


async def test_unlimited_pagination_returns_none_limit_in_result(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    select_many_repo_call(total=5, users=[_make_orm_user() for _ in range(5)])

    result = await use_case(
        SelectManyUserRequest(pagination=OffsetPagination(limit=None))
    )

    assert result.limit is None
    assert result.total == 5
    assert len(result.data) == 5


async def test_default_request_uses_default_pagination(
    use_case: SelectManyUserUseCase, select_many_repo_call: Any
) -> None:
    select_many_repo_call(total=0, users=[])

    await use_case(SelectManyUserRequest())

    kwargs = select_many_repo_call.captured["kwargs"]
    assert kwargs["offset"] == 0
    assert kwargs["limit"] is None
    assert kwargs["order_by"] == "desc"
    assert kwargs["login"] is None
    assert kwargs["role_uuid"] is None
