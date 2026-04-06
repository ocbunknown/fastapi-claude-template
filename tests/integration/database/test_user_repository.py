from __future__ import annotations

from typing import Callable

import pytest
import uuid_utils.compat as uuid

from src.application.common.exceptions import ConflictError, NotFoundError
from src.database.psql import DBGateway


async def test_create_user(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    async with database:
        role = (await database.role.select(name="User")).result()
        user = (
            await database.user.create(
                login=unique_login(),
                password="hashed",
                role_uuid=role.uuid,
            )
        ).result()

    assert user.uuid is not None
    assert user.active is True


async def test_create_duplicate_login_raises_conflict(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    login = unique_login()

    async with database:
        role = (await database.role.select(name="User")).result()
        await database.user.create(
            login=login, password="hashed", role_uuid=role.uuid
        )

    with pytest.raises(ConflictError):
        async with database:
            role = (await database.role.select(name="User")).result()
            await database.user.create(
                login=login, password="hashed", role_uuid=role.uuid
            )


async def test_select_nonexistent_user_raises_not_found(
    database: DBGateway,
) -> None:
    with pytest.raises(NotFoundError):
        async with database.manager.session:
            (await database.user.select(user_uuid=uuid.uuid4())).result()


async def test_select_many_unlimited_returns_all_rows(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    """Repository must honour ``limit=None`` and return every matching row,
    so internal callers (other use cases, scheduled tasks) can iterate over
    the full table without paging."""
    seeded = 25

    async with database:
        role = (await database.role.select(name="User")).result()
        for _ in range(seeded):
            await database.user.create(
                login=unique_login(), password="hashed", role_uuid=role.uuid
            )

    async with database.manager.session:
        total, users = (
            await database.user.select_many(limit=None)
        ).result()

    assert total >= seeded
    assert len(users) == total


async def test_select_many_with_finite_limit_caps_results(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    """When called via the public HTTP path the strict contract enforces
    ``limit ≤ 200``; the repository must respect whatever finite limit it
    receives."""
    async with database:
        role = (await database.role.select(name="User")).result()
        for _ in range(15):
            await database.user.create(
                login=unique_login(), password="hashed", role_uuid=role.uuid
            )

    async with database.manager.session:
        total, users = (
            await database.user.select_many(limit=10)
        ).result()

    assert total >= 15
    assert len(users) == 10


async def test_select_many_filters_by_login_substring(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    needle = unique_login()

    async with database:
        role = (await database.role.select(name="User")).result()
        await database.user.create(
            login=needle, password="hashed", role_uuid=role.uuid
        )
        await database.user.create(
            login=unique_login(), password="hashed", role_uuid=role.uuid
        )

    async with database.manager.session:
        total, users = (
            await database.user.select_many(login=needle, limit=None)
        ).result()

    assert total == 1
    assert users[0].login == needle
