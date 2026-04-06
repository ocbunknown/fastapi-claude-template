from __future__ import annotations

import httpx


async def test_register_login_me_flow(client: httpx.AsyncClient) -> None:
    register_response = await client.post(
        "/v1/auth/register",
        json={
            "login": "alice",
            "password": "supersecret",
            "fingerprint": "browser-fp-1",
        },
    )
    assert register_response.status_code == 200, register_response.text
    assert register_response.json() == {"status": True}


async def test_healthcheck_is_public(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"status": True}


async def test_users_me_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/users/me")
    assert response.status_code == 401


async def test_admin_endpoints_require_admin_role(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/admin/users")
    assert response.status_code == 401
