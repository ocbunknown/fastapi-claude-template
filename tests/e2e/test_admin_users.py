from __future__ import annotations

from typing import Callable

import httpx

from src.application.common.interfaces.hasher import Hasher
from src.database.psql import DBGateway


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_select_users_returns_paginated_envelope(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    response = await client.get("/v1/admin/users", headers=_auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"data", "offset", "limit", "total"}
    assert isinstance(body["data"], list)
    assert body["offset"] == 0
    assert body["limit"] == 10  # contract default
    assert body["total"] >= 1  # at least the seeded admin


async def test_select_users_loads_role_when_requested(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    response = await client.get(
        "/v1/admin/users",
        params={"loads": ["role"]},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    users = response.json()["data"]
    assert users, "expected at least the seeded admin"
    assert all("role" in u for u in users)
    assert any(u["role"]["name"] == "Admin" for u in users)


async def test_select_users_omits_role_by_default(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    """Without ``loads=role`` the relationship is not eager-loaded; the
    response serializer (``exclude_none=True``) drops the field entirely."""
    response = await client.get("/v1/admin/users", headers=_auth(admin_token))

    assert response.status_code == 200
    users = response.json()["data"]
    assert users, "expected at least the seeded admin"
    assert all("role" not in u for u in users)


async def test_select_users_filter_by_login_substring(
    client: httpx.AsyncClient,
    admin_token: str,
    database: DBGateway,
    unique_login: Callable[[], str],
    hasher: Hasher,
) -> None:
    needle = unique_login()
    async with database:
        role = (await database.role.select(name="User")).result()
        await database.user.create(
            login=needle,
            password=hasher.hash_password("x"),
            role_uuid=role.uuid,
        )

    response = await client.get(
        "/v1/admin/users",
        params={"login": needle},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["data"][0]["login"] == needle


async def test_select_users_pagination_offset_limit(
    client: httpx.AsyncClient,
    admin_token: str,
    database: DBGateway,
    unique_login: Callable[[], str],
    hasher: Hasher,
) -> None:
    async with database:
        role = (await database.role.select(name="User")).result()
        for _ in range(15):
            await database.user.create(
                login=unique_login(),
                password=hasher.hash_password("x"),
                role_uuid=role.uuid,
            )

    response = await client.get(
        "/v1/admin/users",
        params={"offset": 5, "limit": 10},
        headers=_auth(admin_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["offset"] == 5
    assert body["limit"] == 10
    assert len(body["data"]) == 10
    assert body["total"] >= 16  # 15 seeded + admin


async def test_select_users_rejects_limit_below_min(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    """Project converts ``RequestValidationError`` to 400 (not the default
    422); see ``presentation/http/common/exception_handlers.py``."""
    response = await client.get(
        "/v1/admin/users",
        params={"limit": 5},
        headers=_auth(admin_token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Validation error"
    assert body["detail"][0]["loc"] == ["query", "limit"]
    assert "greater than or equal to 10" in body["detail"][0]["msg"]


async def test_select_users_rejects_limit_above_max(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    response = await client.get(
        "/v1/admin/users",
        params={"limit": 500},
        headers=_auth(admin_token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"][0]["loc"] == ["query", "limit"]
    assert "less than or equal to 200" in body["detail"][0]["msg"]


async def test_select_users_rejects_negative_offset(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    response = await client.get(
        "/v1/admin/users",
        params={"offset": -1},
        headers=_auth(admin_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"][0]["loc"] == ["query", "offset"]


async def test_select_users_rejects_invalid_order_by(
    client: httpx.AsyncClient,
    admin_token: str,
) -> None:
    response = await client.get(
        "/v1/admin/users",
        params={"order_by": "random"},
        headers=_auth(admin_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"][0]["loc"] == ["query", "order_by"]


async def test_select_users_unauthorized_without_token(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/v1/admin/users")

    assert response.status_code == 401
