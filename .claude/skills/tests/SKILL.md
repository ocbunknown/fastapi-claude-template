---
name: tests
description: Use when creating or extending tests under tests/unit/, tests/integration/, or tests/e2e/. Enforces per-use-case unit coverage, per-endpoint e2e coverage, mutation-persistence verification (not just 200 status), contract-vs-Request field-mismatch detection, loads-opt-in flow tests, role/validation boundary tests, and the test infra gotchas (sync alembic fixture, session-scoped asyncio loop, httpx.AsyncClient + ASGITransport, CipherSettings with matching HS256 keys, argon2 hasher seeding).
---

# Writing tests (`tests/unit/`, `tests/integration/`, `tests/e2e/`)

Tests without rules drift into ceremony — "test exists, test passed, shipping". Real bugs this repo shipped because nobody had a test that exercised the exact scenario:

1. `UserResult.model_validate(orm_user)` in `update.py` / `create.py` / `permission.py` — crashed with `MissingGreenlet` on PATCH/POST. Not caught because the e2e tests only hit GET.
2. `UpdateUserRequest` had only `password` field while `AdminUpdateUser` contract had `password + active + role_uuid` — PATCH silently dropped `active` and `role_uuid` (Pydantic `extra="ignore"`), returned 200, and did nothing. Not caught because no test verified that the mutation **persisted** via a follow-up GET.
3. `select_many` without `loads=role` triggered `MissingGreenlet`. Caught only because an explicit `test_select_users_omits_role_by_default` test existed. Other endpoints had no such test.

Every "why didn't the tests catch this" answer has the same root: **the scenario was never tested**. This skill lists the scenarios that must exist.

## Pick the right layer — don't cross them

| Layer | What it tests | What it uses | Typical runtime |
|---|---|---|---|
| `tests/unit/` | Pure logic: use cases, validators, helpers, contracts | `MagicMock`/`AsyncMock` DBGateway, `FakeHasher`, `FakeJWT`, `FakeStrCache` from `tests/fakes.py` | < 2s for the whole folder |
| `tests/integration/` | Real I/O: repositories against Postgres, Redis adapters, NATS brokers | Session-scoped `testcontainers` (Postgres/Redis/NATS), per-test outer-transaction rollback | 3–10s |
| `tests/e2e/` | Full HTTP stack: endpoint → contract → mediator → use case → repo → DB | Real app wired via Dishka, `httpx.AsyncClient` + `ASGITransport` | 5–15s |

**Hard rules:**
- **Unit tests never touch I/O.** No `await database.X.create(...)` against a real DB — that's integration.
- **Integration tests never go through HTTP.** If you want to test the endpoint wiring, that's e2e.
- **E2E tests never replace unit tests.** Unit tests cover branches fast; e2e tests cover a few happy/sad paths against the real stack. Don't try to cover every validation edge case in e2e — that belongs in unit (for Pydantic contracts) and integration (for DB constraints).

## Unit tests — use cases

For **every** use case under `application/v1/usecases/<domain>/<action>.py` there is a `tests/unit/test_<action>_<entity>_usecase.py` file. **No exceptions.** If a use case has no unit test, it is not considered finished.

### Fixtures

Shared fakes live in `tests/fakes.py` (`FakeHasher`, `FakeJWT`, `FakeStrCache`). Shared fixtures live in `tests/unit/conftest.py` (`fake_cache`, `fake_hasher`, `fake_jwt`, `auth_service`, `services`, `fake_database`, `stub_user`). Reuse them — do not redefine.

### Patterns

**1. Mock `DBGateway.<repo>.<method>` to return the expected ORM stub, capture call kwargs:**

```python
@pytest.fixture
def update_repo_call(fake_database: MagicMock) -> Any:
    captured: dict[str, Any] = {}

    def _stub(user_stub: MagicMock) -> None:
        async def _update(uuid_arg: Any, /, **kwargs: Any) -> MagicMock:
            captured["uuid"] = uuid_arg
            captured["kwargs"] = kwargs
            return MagicMock(result=lambda: user_stub)

        fake_database.user.update = AsyncMock(side_effect=_update)

    _stub.captured = captured  # type: ignore[attr-defined]
    return _stub
```

**2. ORM stub must implement `.as_dict()` to mimic `Base.as_dict()`:**

```python
def _make_orm_user(login: str = "alice", active: bool = True) -> MagicMock:
    user = MagicMock()
    user.uuid = uuid.uuid4()
    user.login = login
    user.active = active
    user.as_dict.return_value = {
        "uuid": user.uuid,
        "login": login,
        "active": active,
    }
    return user
```

Do **not** add `role` to `as_dict.return_value` unless you are specifically testing the eager-loaded case — mimicking the production behavior where unloaded relationships simply aren't in `__dict__`.

**3. Assert what the use case forwards to the repository, not just the return value:**

```python
async def test_update_user_passes_password_hashed(
    use_case: UpdateUserUseCase,
    update_repo_call: Any,
    fake_hasher: FakeHasher,
) -> None:
    update_repo_call(_make_orm_user())

    await use_case(UpdateUserRequest(user_uuid=uuid.uuid4(), password="plain"))

    assert update_repo_call.captured["kwargs"]["password"] == fake_hasher.hash_password("plain")
```

**4. `exclude_unset=True` coverage — when client omits a field, verify it is not forwarded:**

```python
async def test_update_user_omits_unset_fields(
    use_case: UpdateUserUseCase, update_repo_call: Any
) -> None:
    update_repo_call(_make_orm_user())

    await use_case(UpdateUserRequest(user_uuid=uuid.uuid4(), active=False))

    kwargs = update_repo_call.captured["kwargs"]
    assert kwargs == {"active": False}
    assert "password" not in kwargs
    assert "role_uuid" not in kwargs
```

This is the test that would have caught the `AdminUpdateUser → UpdateUserRequest` field-mismatch bug.

### Mandatory scenarios per use case

For **every** use case, unit tests must cover:

- **Happy path** — the primary success case returning the expected `Result` type.
- **Each `if` / `raise` branch** — if the use case raises `NotFoundError` / `ForbiddenError` / `ConflictError`, there is a test that triggers each raise.
- **Kwargs forwarding** — assert the exact kwargs passed to each repo method. Prevents silent field drops.
- **Return type matches declaration** — if the method is typed `-> UserResult`, assert `isinstance(result, UserResult)` and at least one field value.
- **`exclude_unset=True` / `exclude_none=True` semantics** — if the use case selectively forwards fields, test both "included" and "omitted".
- **Pagination propagation** (for `SelectMany*` use cases) — test `limit=None` → repo called with `limit=None`; test default → repo called with default; test strict limits → forwarded as-is.

### Anti-patterns

| ❌ | ✅ |
|---|---|
| Testing `use_case(request)` and only asserting `result.uuid is not None` | Assert the captured repo kwargs against an exact expected dict |
| Using a real DBGateway and a real session in a unit test | That's integration. Move the test. |
| Adding `role` to the ORM stub's `.as_dict()` return when testing "no loads" scenarios | Mimic real behavior — unloaded relations are absent from `__dict__` |
| Hardcoding `uuid.uuid4()` literals as strings in assertions | Capture the generated UUID from the request, compare by reference |
| Testing Pydantic `Field(...)` validators via the use case | Test contracts/requests directly in `test_<contract_or_pagination>.py` — don't go through the use case |

## Integration tests — repositories

For **every** repository method that has non-trivial logic (`select_many` with filters, `select` with multiple `where` branches, `@on_integrity` wrapped methods, Query Objects), there is an integration test. Trivial `insert` / plain `SELECT by uuid` are covered by the repo's unit-typed `_crud` helper and don't need per-column tests.

### Fixtures

- `database: DBGateway` (function scope) from root `tests/conftest.py` — opens a fresh session against the shared testcontainer Postgres, wraps the test in an outer transaction that rolls back at teardown (per-test isolation without explicit cleanup).
- `unique_login: Callable[[], str]` — factory that returns a unique login per call (avoids unique-constraint clashes across test files running in parallel).
- `db_session: AsyncSession` — if you need raw session access.

### Patterns

**1. Seed via `async with database:` (write transaction), assert via `async with database.manager.session:` (read-only) — same request scope:**

```python
async def test_select_many_filters_by_login_substring(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    needle = unique_login()

    async with database:
        role = (await database.role.select(name="User")).result()
        await database.user.create(login=needle, password="hashed", role_uuid=role.uuid)
        await database.user.create(login=unique_login(), password="hashed", role_uuid=role.uuid)

    async with database.manager.session:
        total, users = (await database.user.select_many(login=needle, limit=None)).result()

    assert total == 1
    assert users[0].login == needle
```

**2. Test `limit=None` explicitly** — internal callers rely on it. The contract layer never lets `None` through HTTP, but use cases/tasks do.

```python
async def test_select_many_unlimited_returns_all_rows(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    async with database:
        role = (await database.role.select(name="User")).result()
        for _ in range(25):
            await database.user.create(login=unique_login(), password="hashed", role_uuid=role.uuid)

    async with database.manager.session:
        total, users = (await database.user.select_many(limit=None)).result()

    assert total >= 25
    assert len(users) == total
```

**3. Test `@on_integrity` raises the right domain exception on constraint violation:**

```python
async def test_create_duplicate_login_raises_conflict(
    database: DBGateway, unique_login: Callable[[], str]
) -> None:
    login = unique_login()
    async with database:
        role = (await database.role.select(name="User")).result()
        await database.user.create(login=login, password="hashed", role_uuid=role.uuid)

    with pytest.raises(ConflictError):
        async with database:
            role = (await database.role.select(name="User")).result()
            await database.user.create(login=login, password="hashed", role_uuid=role.uuid)
```

### Mandatory scenarios per repository method

- **`create`** — success + `@on_integrity` raises domain exception on constraint violation.
- **`select`** — by-uuid success, by-uuid not found raises `NotFoundError`, each alternative filter key.
- **`select_many`** — default (no filters), each filter key individually, `limit=None` returns all rows, finite `limit` caps result, `offset` paginates correctly, `order_by="asc"` vs `"desc"`.
- **`update`** — each updatable column individually (not "update all at once" — that would mask silent field drops). For `@on_integrity` methods, include the conflict case.
- **`delete`** — success + not found.

## E2E tests — endpoints

For **every** endpoint function in `presentation/http/v1/endpoints/<audience>/<file>.py` there is at least one happy-path e2e test. For mutating endpoints (POST/PATCH/PUT/DELETE), there must also be a **mutation-persistence test** that follows the mutation with a GET and verifies the change landed in the DB.

### Infra notes (load-bearing — don't break these)

- **`httpx.AsyncClient` + `httpx.ASGITransport`**, not `TestClient`. `TestClient` bridges sync→async through anyio's portal, which spawns its own loop; asyncpg connections made in the test's session-scoped loop crash with "attached to a different loop" inside the portal. `ASGITransport` runs the app in the same loop as the test.
- **Alembic migrations run in a sync session-scoped fixture** (`_migrate_database`), not inside the async `db_engine` fixture — `migrations/env.py` uses `asyncio.run` internally and it explodes inside an already-running event loop.
- **`pyproject.toml` sets `asyncio_default_test_loop_scope = "session"`** to keep the asyncpg connection loop consistent across tests and fixtures.
- **`cipher_settings` fixture generates a valid base64 HS256 key and sets `CIPHER_SECRET_KEY == CIPHER_PUBLIC_KEY`** — `JWT.create` signs with `secret_key`, `JWT.verify_token` decodes with `public_key`, symmetric HS256 needs them identical.
- **The real `Hasher` (Argon2) is pulled from the e2e container** via the `hasher` fixture — fake hashers would not be recognised by the login use case which uses the real Argon2 verifier.

### Auth fixtures

The e2e conftest ships three chained fixtures that you reuse — do not re-implement auth per test:

- **`hasher: Hasher`** — resolves the real Argon2 hasher from the e2e container.
- **`admin_credentials: tuple[str, str]`** — seeds an Admin-role user directly via `DBGateway` (bypassing the 2-step register/confirm flow that needs an out-of-band verification code) and returns `(login, password)`.
- **`admin_token: str`** — logs in as the seeded admin via `POST /v1/auth/login` and returns the bearer access token.

For user-role tests (non-admin), seed via `database` + `hasher` directly in the test body using the same pattern.

### Patterns

**1. Happy path + envelope shape:**

```python
async def test_select_users_returns_paginated_envelope(
    client: httpx.AsyncClient, admin_token: str
) -> None:
    response = await client.get("/v1/admin/users", headers=_auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"data", "offset", "limit", "total"}
    assert body["offset"] == 0
    assert body["limit"] == 10  # contract default
```

**2. Mutation-persistence — the rule that would have caught the `UpdateUserRequest` field-mismatch bug:**

```python
async def test_update_user_active_flag_persists(
    client: httpx.AsyncClient,
    admin_token: str,
    database: DBGateway,
    unique_login: Callable[[], str],
    hasher: Hasher,
) -> None:
    login = unique_login()
    async with database:
        role = (await database.role.select(name="User")).result()
        user = (await database.user.create(
            login=login, password=hasher.hash_password("x"), role_uuid=role.uuid,
        )).result()

    patch = await client.patch(
        f"/v1/admin/users/{user.uuid}",
        headers=_auth(admin_token),
        json={"active": False},
    )
    assert patch.status_code == 200
    assert patch.json()["active"] is False

    get = await client.get(
        "/v1/admin/users",
        headers=_auth(admin_token),
        params={"login": login},
    )
    assert get.status_code == 200
    assert get.json()["data"][0]["active"] is False
```

**Never** write a PATCH/POST/DELETE e2e test that only asserts `response.status_code == 200`. Always follow up with a GET (or the same endpoint) that proves the mutation landed. 200 without persistence is what bit us on `AdminUpdateUser.active` — the endpoint returned 200 and silently dropped the field.

**3. Test `loads=` opt-in / opt-out both ways:**

```python
async def test_select_users_omits_role_by_default(
    client: httpx.AsyncClient, admin_token: str
) -> None:
    response = await client.get("/v1/admin/users", headers=_auth(admin_token))
    assert response.status_code == 200
    users = response.json()["data"]
    assert all("role" not in u for u in users)  # exclude_none drops unloaded


async def test_select_users_loads_role_when_requested(
    client: httpx.AsyncClient, admin_token: str
) -> None:
    response = await client.get(
        "/v1/admin/users", headers=_auth(admin_token), params={"loads": ["role"]},
    )
    assert response.status_code == 200
    users = response.json()["data"]
    assert all("role" in u for u in users)
```

The "without loads" test is the one that catches `model_validate(orm)` → `MissingGreenlet` bugs. **Every** endpoint that has optional `loads` must have both sides tested.

**4. Contract validation boundaries — for every strict field, test both sides of the constraint:**

```python
async def test_select_users_rejects_limit_below_min(
    client: httpx.AsyncClient, admin_token: str
) -> None:
    response = await client.get(
        "/v1/admin/users", headers=_auth(admin_token), params={"limit": 5},
    )
    assert response.status_code == 400  # project converts RequestValidationError to 400
    body = response.json()
    assert body["message"] == "Validation error"
    assert body["detail"][0]["loc"] == ["query", "limit"]
    assert "greater than or equal to 10" in body["detail"][0]["msg"]
```

**Not 422.** The project converts `RequestValidationError` to **400** in `presentation/http/common/exception_handlers.py`. If you assert 422, the test will be wrong even when the logic is correct.

**5. Authorization matrix — for every non-public endpoint:**

```python
async def test_select_users_unauthorized_without_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/admin/users")
    assert response.status_code == 401


async def test_admin_endpoint_rejects_user_role_token(
    client: httpx.AsyncClient,
    database: DBGateway,
    hasher: Hasher,
    unique_login: Callable[[], str],
) -> None:
    login = unique_login()
    async with database:
        role = (await database.role.select(name="User")).result()
        await database.user.create(
            login=login, password=hasher.hash_password("pw"), role_uuid=role.uuid,
        )
    login_resp = await client.post(
        "/v1/auth/login",
        json={"login": login, "password": "pw", "fingerprint": "test"},
    )
    user_token = login_resp.json()["token"]

    response = await client.get("/v1/admin/users", headers=_auth(user_token))
    assert response.status_code == 401  # this project returns 401 "Not Allowed", not 403
```

### Mandatory scenarios per endpoint

For **every** endpoint function:

- **Happy path** returning expected shape (and checking the response contract is not leaking fields that shouldn't be there — `password`, `role_uuid` in a user-facing response, etc.).
- **Unauthorized 401** (unless the endpoint is in `public/`).
- **Wrong role 401** if the endpoint is in `admin/` — hit it with a user-role token.
- **Contract validation 400** for at least one constraint boundary (min, max, literal, required field missing).

For **list** endpoints additionally:
- **Default pagination** returns contract defaults (`offset=0, limit=10`).
- **`limit` boundary** (`< MIN_PAGINATION_LIMIT` → 400, `> MAX_PAGINATION_LIMIT` → 400).
- **Negative offset** → 400.
- **Invalid `order_by`** → 400.
- **`loads=` opt-in populates relation**, opt-out (default) omits it (catches `model_validate(orm)` lazy-load).
- **Filter field passes through** — seed 2 users, filter by one, assert only one returned.
- **`offset`/`limit` pagination math** — seed 15+ users, request `offset=5&limit=10`, assert `len(data) == 10` and `total >= 15`.

For **mutation** endpoints (POST/PATCH/PUT/DELETE) additionally:
- **Mutation-persistence** — follow the mutation with a GET; assert the change persisted.
- **Each contract field individually** — PATCH `{only_this_field: value}` for each field in the contract, verify each persists. Catches the Request-vs-Contract field mismatch bug.
- **Partial update preserves untouched fields** — PATCH `{active: false}` on a user, verify `login` and `role` are unchanged in the follow-up GET.

### Anti-patterns

| ❌ | ✅ |
|---|---|
| `assert response.status_code == 422` on a validation error | 400 — the project's exception handler converts `RequestValidationError` to 400 |
| `assert response.status_code == 200` as the only assertion on a PATCH | Follow up with a GET and assert the field actually changed in the DB |
| Using `TestClient(app)` | `httpx.AsyncClient(transport=httpx.ASGITransport(app=e2e_app), base_url="http://testserver")` |
| Asserting `body["detail"] == "Validation error"` | `body["detail"]` is a list of Pydantic error dicts; use `body["detail"][0]["loc"] == ["query", "limit"]` style |
| Testing admin endpoints only with `admin_token` | Also test 401 (no token) and 401 (user-role token) to prove the guard actually gates |
| Re-implementing login/register inline in each test | Use `admin_credentials` / `admin_token` fixtures |
| Assuming `role` field is in the response without `loads=role` | The serializer (`exclude_none=True`) drops None fields — assert `"role" not in user` when no loads, not `user["role"] is None` |
| Hitting the real NATS broker for pub/sub tests from unit layer | Consumer logic in unit (with mocks), broker publish in integration, end-to-end message delivery only where it matters |

## Contract and pagination unit tests

`tests/unit/test_pagination.py` and per-entity `test_<entity>_contract.py` files test Pydantic models directly — no mocks, no use cases, just Pydantic validation.

Mandatory scenarios for a filter/pagination contract:

- **Defaults** — `Contract()` instantiates cleanly with all expected defaults.
- **Each `Field(...)` constraint on both sides** — `ge` rejects below, accepts at, rejects above `le`.
- **`Literal[...]` fields** reject unknown values.
- **Frozen** — mutating a field raises `ValidationError`.
- **Round-trip mapping** (when a Contract maps to an application Request) — `AppRequest(**contract.model_dump())` produces a valid Request, and contract strict bounds translate to valid Request values.

## Mandatory coverage — the new-feature checklist

When you finish a feature, **all of these** exist before you're done:

- [ ] `tests/unit/test_<action>_<entity>_usecase.py` — one file per use case, covering all mandatory scenarios above.
- [ ] `tests/unit/test_<contract_or_thing>.py` — for any new Pydantic contract with validators, pagination type, or pure helper class (e.g. `OffsetResult.map`).
- [ ] `tests/integration/database/test_<entity>_repository.py` — extended with tests for any new repo method or new filter.
- [ ] `tests/e2e/test_<audience>_<entity>.py` — one test file per `<audience>/<entity>.py` endpoint module, covering happy path / auth matrix / validation / mutation persistence / loads opt-in-out.
- [ ] For admin endpoints: the user-role-token rejection test.
- [ ] For mutation endpoints: the mutation-persistence test.
- [ ] For list endpoints: `loads=` opt-in/opt-out tests.
- [ ] `uv run pytest` passes (all three layers, parallel via xdist).
- [ ] `uv run mypy src/ tests/` is clean.
- [ ] `uv run ruff check src/ tests/` is clean.

## Running tests

```bash
uv run pytest                       # whole suite, parallel (xdist auto)
uv run pytest tests/unit/ -q        # unit only, ~1s
uv run pytest tests/integration/    # integration only (needs Docker for testcontainers)
uv run pytest tests/e2e/            # e2e only (needs Docker)
uv run pytest tests/e2e/test_admin_users.py::test_update_user_active_flag_persists  # single test
uv run pytest -k "update"           # by expression
uv run pytest -m unit               # by marker
uv run pytest -o addopts=           # disable xdist + addopts from pyproject (for -v / --tb=long debugging)
```

The xdist parallelism (`-n auto --dist loadfile`) distributes by file, so tests within one file share fixtures. If a test is flaky under xdist, first check whether it leaks state into a session-scoped fixture. Per-test isolation via the `database` outer-transaction rollback is the default — if your integration test commits manually or uses a fresh session, it will leak.
