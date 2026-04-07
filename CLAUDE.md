# FastAPI Template — Architecture Guide

## High-level structure

```
src/
├── application/          ← USE CASES (transport-agnostic business logic)
│   ├── common/
│   │   ├── interfaces/   ← ports: bus, request_bus, event_bus, wrapper, usecase, cache, hasher, jwt, broker
│   │   ├── bus/          ← RequestBusImpl, EventBusImpl (both inherit Bus[M])
│   │   ├── events/       ← Event base, BrokerEvent, StreamEvent, @event decorator
│   │   ├── pagination.py ← OffsetPagination (lenient, internal)
│   │   ├── exceptions.py ← AppException + DetailedError hierarchy
│   │   └── request.py    ← Request base (Pydantic, frozen)
│   ├── v1/
│   │   ├── usecases/     ← use case classes, grouped by domain (auth/, user/)
│   │   ├── services/     ← domain services (AuthService) + ServiceGateway
│   │   ├── results/      ← use case return types (UserResult, OffsetResult, etc.)
│   │   ├── events/       ← v1 domain events (UserRegistered, etc.)
│   │   └── constants.py
│   └── provider.py       ← ApplicationProvider (Dishka)
│
├── infrastructure/       ← OUTBOUND ADAPTERS (accessed through ports)
│   ├── cache/            ← Redis adapter (implements StrCache port)
│   ├── security/         ← JWT, Argon2 (implement JWT, Hasher ports)
│   ├── http/             ← HTTP client stack
│   │   ├── clients/      ← Client + Request base classes (provider-agnostic)
│   │   └── provider/     ← AsyncProvider Protocol + AiohttpProvider + middleware chain
│   ├── broker/nats/      ← NatsBroker, NatsJetStreamBroker
│   ├── logging/          ← setup_logging
│   └── provider.py       ← InfrastructureProvider (Dishka)
│
├── database/             ← PERSISTENCE — first-class layer (see "Persistence")
│   └── psql/             ← SQLAlchemy + Postgres (the only backend)
│       ├── models/       ← ORM models (inherit Base with .as_dict())
│       ├── repositories/ ← repository implementations (BaseRepository + CRUD helper)
│       ├── queries/      ← Query Object pattern (complex SQL builders)
│       ├── types/        ← OrderBy, Loads literals, TypedDict payloads
│       ├── interfaces/   ← internal ports (DBGateway, CRUD)
│       ├── manager.py    ← TransactionManager
│       ├── connection.py ← engine + session factory
│       ├── exceptions.py ← integrity-error translation to AppException
│       ├── tools.py      ← on_integrity decorator + sqla-autoloads re-exports (sqla_select, sqla_offset_query, sqla_cursor_query, unique_scalars, add_conditions)
│       └── provider.py   ← DatabaseProvider (Dishka)
│
├── presentation/         ← INBOUND ADAPTERS — synchronous client interface
│   └── http/             ← FastAPI HTTP transport
│       ├── common/       ← middlewares, serializers (exclude_none=True), guards, contract.py, responses, exception_handlers
│       └── v1/
│           ├── contracts/      ← Pydantic request/response schemas + pagination.py (strict OffsetPagination)
│           ├── guards/         ← v1-specific gates (Authorization JWT+roles)
│           └── endpoints/      ← audience-first organization (see below)
│               ├── public/         no auth (healthcheck, register, login, refresh)
│               ├── user/           JWT, any role (router-level Authorization())
│               ├── admin/          JWT + Admin role (router-level Authorization("Admin"))
│               └── internal/       service-to-service stub (include_in_schema=False)
│
├── consumers/            ← INBOUND ADAPTERS — message-driven (FastStream)
│   ├── routers/          ← @subscriber-decorated functions calling request_bus
│   ├── subjects.py       ← NATS subject constants
│   └── streams.py        ← NATS JetStream stream constants
│
├── tasks/                ← INBOUND ADAPTERS — time-driven (Taskiq)
│   ├── broker.py         ← Taskiq broker + scheduler factories
│   └── *.py              ← scheduled task functions calling request_bus
│
├── entrypoints/          ← composition root + module-level app instances
│   ├── container.py      ← build_container() — shared across all transports
│   ├── http.py           ← FastAPI app + lifespan + run()
│   ├── consumers.py      ← FastStream app
│   ├── tasks.py          ← Taskiq broker + scheduler
│   └── server/           ← ASGI server runners (granian) — process bootstrap
│
├── common/               ← shared leaf utilities (no upper-layer deps)
│   ├── di/               ← Dishka helpers (DynamicContainer, Depends marker, inject)
│   └── tools/            ← formatter, cache key builder, text utils, types
│
└── settings/             ← Pydantic Settings + SettingsProvider
```

## Layer dependency rules

Dependencies point **inward** — outer layers depend on inner layers, never reverse.

```
   presentation/  consumers/  tasks/   ← inbound adapters (outer)
              ↓        ↓        ↓
              └────────┼────────┘
                       ↓
                 application/   ← use cases (inner)
                       ↑   ↘
                       ↑    └──→ database/  ← shared kernel (see exception)
              ┌────────┘
              ↑
       infrastructure/    ← outbound adapters accessed through ports
```

| Layer | Imports allowed from | NOT allowed from |
|---|---|---|
| `application/` | `common/`, `settings/`, `database/` (exception) | inbound adapters, `infrastructure/` |
| `presentation/`, `consumers/`, `tasks/` | `application/`, `database/`, `common/`, `settings/`, `infrastructure/` | each other |
| `infrastructure/` | `application/` (ports/types/exceptions/events), `common/`, `settings/` | inbound adapters, `database/` |
| `database/` | `application/` (exceptions only), `common/`, `settings/` | inbound adapters, `infrastructure/` |
| `entrypoints/` | everything (composition root) | — |
| `common/` | `settings/` | upper layers |
| `settings/` | nothing | — |

**The `infrastructure → application` rule:** outer layers import application's types/ports/exceptions/events to conform to its vocabulary (Dependency Inversion). Application defines `Hasher` Protocol — infrastructure imports it and provides `Argon2`. Same for `Cache`, `JWT`, `EventBus`, `BrokerEvent`.

## Persistence — `database/` as a first-class layer

`database/` is a **top-level layer**, not part of `infrastructure/`. It's a shared kernel for persistence vocabulary — `application/` use cases import `DBGateway`, repository types, `Loads` literals, the `Roles` type alias (`Literal["Admin", "User"]`), TypedDicts, and Query Objects directly. This is **the only allowed inner→outer-style import in the project**.

**Why:** persistence vocabulary (Loads, OrderBy, Create/Update payloads) describes the data model. Mirroring it in `application/` would double maintenance cost. Repository methods are tightly coupled to ORM features (eager loading, CTE, subqueries) — wrapping in Protocols loses type info without gaining swappability we don't need. SQLAlchemy + Postgres is a chosen, stable foundation.

**Scope:** the exception covers **only** `database/`. All other infrastructure (cache, security, broker, http clients, logging) **must** be accessed through Protocols defined in `application/common/interfaces/`. The only import `database/` takes from `application/` is `application.common.exceptions` — `tools.on_integrity` translates `IntegrityError` into `ConflictError`/`AppException` so repositories can raise domain-typed errors. Domain events and Results live entirely inside `application/` and are never touched by `database/`.

Repository methods return ORM models. Use cases map them to Results via `{Entity}Result(**orm.as_dict())` — see "Mapping ORM → Result" below.

## DBGateway — usage rules

`DBGateway` wraps a single SQLAlchemy session with two context managers. **Misusing them causes production bugs**: nested sessions, double commits, lost rollbacks, lazy-load errors.

**Two context managers:**

1. **`async with self.database:`** — opens a **transaction** (`session.begin`). Use for **mutations** (INSERT/UPDATE/DELETE). Auto-commits on success, auto-rollbacks on exception.
2. **`async with self.database.manager.session:`** — opens just the **session context** without a transaction. Use for **read-only** queries.

**Lifecycle:** `DBGateway` is request-scoped (one per HTTP request / consumer message / task invocation). It owns **one** SQLAlchemy session, single-use. Open it **exactly once** per use case. Do not nest, re-enter, or interleave the two context managers.

### Pattern 1 — read-only

```python
async def __call__(self, request: SelectUserRequest) -> UserResult:
    async with self.database.manager.session:
        user = (
            await self.database.user.select(*request.loads, user_uuid=request.user_uuid)
        ).result()
        return UserResult(**user.as_dict())
```

### Pattern 2 — write

```python
async def __call__(self, request: CreateUserRequest) -> UserResult:
    async with self.database:
        user = (
            await self.database.user.create(
                login=request.login,
                password=self.hasher.hash_password(request.password),
                role_uuid=request.role_uuid,
            )
        ).result()
        return UserResult(**user.as_dict())
```

### Pattern 3 — read then write (single transaction)

When a write needs data that was just read, put **both** in one `async with self.database:` block — one session, one transaction, atomic.

```python
async with self.database:
    role = (await self.database.role.select(name="User")).result()      # read
    user = (await self.database.user.create(role_uuid=role.uuid, ...)).result()  # write
```

**Do not** open the session twice (once for read, once for write) — the session is single-use and the second `async with` fails on a closed session.

### ❌ Anti-patterns

| Anti-pattern | Why it breaks | Fix |
|---|---|---|
| Opening the session twice | Second `async with` fails on closed session | Combine into one `async with self.database:` |
| Nesting `async with self.database:` and `.manager.session:` | Double-enter on the same session | Pick one — for writes, `async with self.database:` |
| Calling `self.database.X` outside any context | Session state undefined | Wrap in the appropriate context |
| `{Entity}Result.model_validate(orm_row)` on an ORM row | Pydantic's `from_attributes` calls `getattr(row, "rel")`, triggers lazy load on async session → `MissingGreenlet` | Use `{Entity}Result(**orm_row.as_dict())` — reads `__dict__` only |
| Mutating inside `.manager.session:` | No `session.begin()` → no commit → silent data loss | Switch to `async with self.database:` |

**Rule of thumb:** when in doubt, use `async with self.database:`. Works for both reads and writes, just adds a transaction wrapper. Use `.manager.session:` only when you're certain there's no mutation.

## Mapping ORM → Result: use `Base.as_dict()`

**Never** call `{Entity}Result.model_validate(orm_row)` on a SQLAlchemy ORM instance. Pydantic's `from_attributes=True` walks declared fields via `getattr`, which triggers SQLAlchemy lazy loading inside an async session and crashes with `MissingGreenlet`.

**Always** use the ORM's `Base.as_dict()` helper (defined in `src/database/psql/models/base/core.py`):

```python
# single
return UserResult(**user.as_dict())

# list
data=[UserResult(**u.as_dict()) for u in users]
```

**Why this works:**
- `as_dict()` iterates `self.__dict__` directly. SQLAlchemy populates `__dict__` only with **loaded** attributes — columns always, relationships **only if eagerly fetched**. No `getattr`, no lazy load.
- Nested `Base` instances are recursively converted to dicts; Pydantic auto-coerces them into the corresponding Result type.
- Pydantic v2 defaults to `extra="ignore"`, so extra columns (`password`, `created_at`, `role_uuid`, …) silently drop.
- Missing relationship in dict → Pydantic applies the field default (`role: RoleResult | None = None`).

**Load contract:** the caller decides which relations appear via `loads=...`. Without `loads=role`, the field is `None` and the response serializer (`exclude_none=True`) drops it from the JSON entirely. **Do not** defensively `inspect(orm).unloaded` — that's the caller's job via `loads`.

## HTTP endpoints — audience-first organization

Endpoints are grouped by **audience** (who is allowed to call them), not by feature. Each audience folder owns its router-level guards (auth, role check, rate limit) — policy is obvious from the folder structure and impossible to forget on individual endpoints.

```
presentation/http/v1/endpoints/
├── public/         no auth — healthcheck, register, login, refresh
├── user/           JWT, any role — /me, logout, user-owned resources
├── admin/          JWT + Admin role — admin user management
└── internal/       service-to-service stub (include_in_schema=False)
```

Each audience subfolder has a `setup_<audience>_router()` that builds an `APIRouter` with router-level dependencies. Auth is applied **once** at the router level, not on each endpoint:

```python
# v1/endpoints/admin/__init__.py
def setup_admin_router() -> APIRouter:
    router = APIRouter(
        prefix="/admin",
        dependencies=[Require(Authorization("Admin"))],   # ← all endpoints inherit
    )
    router.include_router(admin_user_router)
    return router
```

`user/` uses `Authorization()` (any authenticated user), `public/` has no guard, `internal/` sets `include_in_schema=False`. All audience routers are composed under `/v1` in `setup_v1_routers()`.

**Receiving the user object:** router-level `Authorization()` validates the JWT but doesn't forward the user object. If the endpoint needs it, declare as a parameter — FastAPI caches the dependency per request, JWT is validated once:

```python
async def get_me_endpoint(
    request_bus: Depends[RequestBus],
    user: Annotated[UserResult, Require(Authorization())],   # cached, no double work
) -> OkResponse[contracts.User]:
    result = await request_bus.send(SelectUserRequest(user_uuid=user.uuid, loads=("role",)))
    return OkResponse(contracts.User.model_validate(result))
```

### Guards

Anything that decides "should this request proceed" is a **guard** — applied as FastAPI dependencies on routers or endpoints. Version-agnostic guards (e.g. `RateLimit`) live in `presentation/http/common/guards/`. v1-specific guards (e.g. `Authorization`) live in `presentation/http/v1/guards/`.

`Authorization` is one merged class for both pure auth and role check:

```python
Authorization()                     # any authenticated user
Authorization("Admin")              # Admin role required
Authorization("Admin", "Moderator") # Admin or Moderator
```

The variadic `*roles` is forwarded to `PermissionRequest.permissions`. Empty tuple = no role check, just JWT validation.

### Adding a new audience

1. Create `v1/endpoints/<audience>/`
2. Add `setup_<audience>_router()` with `prefix=`, `dependencies=[Require(<Guard>())]`, `tags=["<Audience> | <Resource>"]`, optionally `include_in_schema=False`
3. Add new auth mechanism as a guard in `v1/guards/` or `common/guards/` if needed
4. Register in `setup_v1_routers()`

## List endpoints — query, pagination, loads

List endpoints have a fixed shape. Single endpoints (`select`) follow a slimmer version of the same rules.

### Naming (single vs list)

| Layer | Single | List |
|---|---|---|
| Endpoint function | `select_user_endpoint` | `select_users_endpoint` |
| HTTP query Contract | — (path uuid + `loads` only) | `SelectUsers` (plural) |
| Use case Request | `SelectUserRequest` | `SelectManyUserRequest` |
| Use case class | `SelectUserUseCase` | `SelectManyUserUseCase` |
| Result | `UserResult` | `OffsetResult[UserResult]` |

The presentation contract uses **plural** (`SelectUsers`) — the HTTP shape from the client's perspective. The application Request/UseCase keep the `SelectMany*` convention — the use case from the domain perspective. Different layers, different vocab.

### The five-parameter list endpoint shape

```python
@admin_user_router.get(
    "",
    response_model=OffsetResult[contracts.User],
    status_code=status.HTTP_200_OK,
)
async def select_users_endpoint(
    request_bus: Depends[RequestBus],
    query: Annotated[contracts.SelectUsers, Require(contracts.SelectUsers)],
    pagination: Annotated[
        contracts.OffsetPagination, Require(contracts.OffsetPagination)
    ],
    loads: tuple[UserLoads, ...] = Query(default=(), title="Additional relations"),
) -> OkResponse[OffsetResult[contracts.User]]:
    result: OffsetResult[UserResult] = await request_bus.send(
        SelectManyUserRequest(
            loads=loads,
            **query.model_dump(),
            pagination=OffsetPagination(**pagination.model_dump()),
        )
    )
    return OkResponse(result.map(contracts.User.model_validate))
```

**Parameter naming rule:** `query` for `GET` query-string filter groups, `data` for `POST/PATCH/PUT` bodies. Never `queries`, `params`, `body`, `payload`.

**FastAPI dependency parsing:** `Annotated[ContractClass, Require(ContractClass)]` makes FastAPI introspect the Pydantic model's fields and surface each primitive field as a separate query parameter in OpenAPI. Works for `str | None`, `UUID | None`, `int`, `Literal[...]`. Complex/nested types are not supported in query strings — keep filter contracts flat.

**`loads` is a separate `Query` parameter** (not nested in the filter contract) so the frontend can opt in to relations per request. Default `()` = no eager loading. Forward as-is: `loads=loads`.

### Pagination — strict contract, lenient application

Two `OffsetPagination` classes with the same name in two different layers:

| Layer | Class | Purpose | Bounds |
|---|---|---|---|
| `presentation/http/v1/contracts/pagination.py` | `OffsetPagination` (Contract) | Public HTTP input | `offset ≥ 0`, `10 ≤ limit ≤ 200`, default `limit=10` |
| `application/common/pagination.py` | `OffsetPagination` (Pydantic, frozen) | Internal use case input | `limit: int \| None = None`, no upper bound |

The endpoint maps strict → lenient via `OffsetPagination(**pagination.model_dump())`. Unqualified `OffsetPagination` in the endpoint module refers to the **application** class (imported directly); `contracts.OffsetPagination` refers to the strict contract — no name collision.

When `limit=None` (internal path), the repository honours it: `select_many` accepts `limit: Optional[int] = None` and SQLAlchemy's `.limit(None)` returns all rows. `OffsetResult[T].limit` is `int | None` for the unbounded case.

**Rule:** never expose unbounded pagination through a public HTTP endpoint. The contract layer is the only door, and it always enforces ≤200.

### Result → Contract mapping

Use case returns `OffsetResult[UserResult]`. Endpoint hands back `OffsetResult[contracts.User]`:

```python
return OkResponse(result.map(contracts.User.model_validate))
```

`OffsetResult.map(fn)` (defined in `application/v1/results/base.py`) takes any `Callable[[T], R]`, applies it to each item in `data`, returns a new `OffsetResult[R]` with the same `offset/limit/total`. The envelope is **layer-agnostic** — there's no separate `contracts.OffsetResult`. Item-level types (`UserResult` ↔ `contracts.User`) stay split because their fields can diverge.

`contracts.User.model_validate(user_result)` works directly on a `UserResult` instance because `Contract` sets `from_attributes=True` — no intermediate `model_dump()` round-trip.

### Adding a new list endpoint — checklist

1. **Repository:** `select_many` accepts `*loads`, filter kwargs, `order_by`, `offset`, `limit: Optional[int] = None`. Honour `limit=None` (no upper cap).
2. **Result:** `{Entity}Result(Result)` in `application/v1/results/`. `OffsetResult[T]` is reused — do not redefine.
3. **Use case:** `SelectMany{Entity}Request` with `loads`, flat filter fields, `pagination: OffsetPagination = OffsetPagination()`. Inside `async with database.manager.session:` call repo with `*request.loads`, filters, `**request.pagination.model_dump()`. Build each item via `{Entity}Result(**orm.as_dict())`.
4. **Filter Contract:** `Select{Entities}(Contract)` — flat primitives only. Re-export from `contracts/__init__.py`.
5. **Endpoint:** five-parameter shape above. Tag `["<Audience> | <Entity>"]`. `response_model=OffsetResult[contracts.{Entity}]`.
6. **Tests:** unit (use case + mocks: kwargs forwarding, `limit=None` propagation, defaults), integration (repo `limit=None` returns all, finite `limit` caps, filter passes through), e2e (envelope shape, `loads` opt-in, strict validation returns **400** — project converts `RequestValidationError` to 400, not FastAPI default 422, unauthorized → 401).

## RequestBus + UseCase pattern

All business operations go through the `RequestBus`. Endpoints, subscribers, and tasks never contain business logic — they translate transport input into a `Request` and call `request_bus.send(request)`. The same bus is used by every transport (HTTP, consumers, tasks), which keeps use cases completely transport-agnostic.

**Bus protocol family (`application/common/interfaces/`):**
- **`Bus[M]`** (`bus.py`) — common parent Protocol with `send(message: M)`.
- **`RequestBus(Bus[Request])`** (`request_bus.py`) — in-process 1→1 request/response. Has `send` + `send_wrapped`.
- **`EventBus(Bus[Event])`** (`event_bus.py`) — 1→N pub/sub via brokers (NATS), fire-and-forget. Has `send` + `send_wrapped`.

**Wrapper protocols (`application/common/interfaces/wrapper.py`):**

Cross-cutting decorators around the unit of work — kept in their own port file because they are an independent abstraction the buses *use*, not part of the bus contract itself.

- **`RequestWrapper[Q: Request, R]`** — `execute(use_case, message) -> R`. Implemented by `ResponseCache`, retry/metrics/idempotency wrappers, etc.
- **`EventWrapper`** — `execute(broker, message) -> None`. For outbox / retry / tracing on event publishing.

Each wrapper uses a **domain-specific parameter name** (`use_case` or `broker`) rather than a generic `handler`, so the wrapper contract reads truthfully for its bus.

**`Request` is the use case's input, not an HTTP request.** It is a transport-agnostic Pydantic model describing what the use case needs. HTTP-shape lives separately in `presentation/http/v1/contracts/` under entity/action names (`Login`, `Register`, `User`, etc.). Do not import `fastapi.Request` and `application.common.request.Request` in the same module.

**UseCase rules:**
1. Inherits `UseCase[Q, R]` where `Q: Request`, `R` is the return type (a `Result` subclass).
2. `@dataclass(slots=True)` — auto-applied by base class, add explicitly for mypy.
3. Dependencies are constructor fields injected by the request bus (`database: DBGateway`, `hasher: Hasher`, etc.).
4. `async def __call__(self, request: Q) -> R` — one use case per file, `Request` class in the same file.
5. Returns a `Result` subclass from `application/v1/results/` — never a `Contract`, never a bare ORM row, never a dict.
6. Registered in `application/v1/usecases/__init__.py::setup_use_cases()` via `request_bus.register(...)`.

**Request rules:** inherits `src.application.common.request.Request` (Pydantic, `frozen=True`). Defined in the same file as its use case. Contains only the fields the use case needs — independent of HTTP/MQ contracts. Validation via Pydantic `Field(...)` constraints.

**Result rules:**
- Inherits `Result` from `application/v1/results/base.py` (Pydantic, `from_attributes=True`, frozen).
- Use case maps ORM → Result via `{Entity}Result(**orm.as_dict())`. **Never** `Result.model_validate(orm_row)` — see "Mapping ORM → Result".
- Endpoints map Result → Contract via `contracts.X.model_validate(result)` — no `model_dump()` round-trip (Contract has `from_attributes=True`).
- Paginated responses: `result.map(contracts.X.model_validate)`.
- Result types are reused across use cases that return the same shape.
- `OffsetResult[T]` is layer-agnostic — defined once in `application/v1/results/base.py` and reused as both use case return type and HTTP response type.

**Inbound adapter rules (endpoints / subscribers / tasks):** all three are **thin adapters** — no business logic, no DB access, no validation beyond schema parsing. They translate transport input into a `Request` and call `request_bus.send()`. HTTP endpoints wrap the result: `OkResponse(contracts.X.model_validate(result))` (single) or `OkResponse(result.map(contracts.X.model_validate))` (list).

### `send` vs `send_wrapped`

Both buses expose two dispatch methods:

- **`send(message)`** — direct dispatch: bus resolves the target (use case / broker) by message type and invokes it. Use this for the default path.
- **`send_wrapped(wrapper, message)`** — wrapped dispatch: bus resolves the target and hands it to a domain-specific wrapper (`RequestWrapper` or `EventWrapper`), which decides *how* to execute (cache, retry, metrics, outbox, dedup, etc.). The wrapper is **bus-agnostic** — it only sees `(use_case, message)` for `RequestBus` or `(broker, message)` for `EventBus`, never the bus itself.

Example — caching an HTTP endpoint via `ResponseCache` wrapper:

```python
async def get_me_endpoint(
    request_bus: Depends[RequestBus],
    cache: Annotated[
        ResponseCache,
        Require(ResponseCache(expires_in=timedelta(seconds=30), key="user:{user_uuid}"))
    ],
    user: Annotated[UserResult, Require(Authorization())],
) -> OkResponse[contracts.User]:
    result = await request_bus.send_wrapped(
        cache,
        SelectUserRequest(user_uuid=user.uuid, loads=("role",)),
    )
    return OkResponse(contracts.User.model_validate(result))
```

The endpoint chooses `send` or `send_wrapped` per call. Wrapper implementations live in `presentation/http/common/wrapper/` and satisfy the `RequestWrapper[Q, R]` Protocol structurally — no explicit subclassing required.

`EventBus.send_wrapped` exists symmetrically (`EventWrapper` with `execute(broker, message)`) for event-level cross-cutting concerns (outbox, retry, tracing), even if no such wrappers exist yet.

## DI composition

- **Each layer has its own Provider** (`application/provider.py`, `infrastructure/provider.py`, `database/psql/provider.py`, `infrastructure/broker/provider.py`, `settings/provider.py`).
- **Composition** in `entrypoints/container.py::build_container(settings, *extras)`. Each entry point (http, consumer, scheduler) calls `build_container()` and adds its framework integration provider (`FastapiProvider`, `FastStreamProvider`, `TaskiqProvider`).
- **Resources with lifecycle** (Redis, DB engine, NATS, aiohttp session) use `@provide` with `yield` — closed automatically when the container closes.
- **Lifespan** in each entry point ends with `await container.close()`.

## Naming conventions

| Entity | Pattern | Example |
|---|---|---|
| Request (single) | `{Action}{Entity}Request` | `LoginRequest`, `SelectUserRequest` |
| Request (list) | `SelectMany{Entity}Request` | `SelectManyUserRequest` |
| UseCase (single) | `{Action}{Entity}UseCase` | `SelectUserUseCase` |
| UseCase (list) | `SelectMany{Entity}UseCase` | `SelectManyUserUseCase` |
| Result | `{Entity}Result` or domain noun | `UserResult`, `TokensExpire` |
| Repository | `{Entity}Repository` | `UserRepository` |
| Service | `{Domain}Service` | `AuthService` |
| Gateway | `{Scope}Gateway` | `ServiceGateway`, `DBGateway` |
| TypedDict payload | `Create{Entity}Type` / `Update{Entity}Type` | `CreateUserType` |
| Contract (body/response) | `{Entity}` or `{Action}` | `User`, `Login`, `Register` |
| Contract (list query) | `Select{Entities}` (plural) | `SelectUsers` |
| Endpoint func (single) | `{action}_{entity}_endpoint` | `select_user_endpoint` |
| Endpoint func (list) | `{action}_{entities}_endpoint` (plural) | `select_users_endpoint` |
| Endpoint param: GET filter | `query` | `query: Annotated[contracts.SelectUsers, Require(...)]` |
| Endpoint param: body | `data` | `data: contracts.AdminUpdateUser` |
| Endpoint param: pagination | `pagination` | `pagination: Annotated[contracts.OffsetPagination, Require(...)]` |
| Endpoint param: relations | `loads` | `loads: tuple[UserLoads, ...] = Query(default=())` |
| Loads literal | `{Entity}Loads` | `UserLoads` |
| OpenAPI tag | `"<Audience> \| <Resource>"` | `"Admin \| User"`, `"Public"` |
| Domain event | `{Entity}{PastTense}` | `UserRegistered` |

## Adding a new feature — checklist

1. `database/models/` — SQLAlchemy model + alembic migration in `migrations/versions/`
2. `database/types/` — `Create{Entity}Type`, `Update{Entity}Type`, `{Entity}Loads`
3. `database/repositories/` — extend `BaseRepository`; methods return `Result[T]`; `select_many` uses `limit: Optional[int] = None`
4. `database/__init__.py` — add property to `DBGateway`
5. `application/v1/results/` — `{Entity}Result(Result)`
6. `application/v1/usecases/{domain}/` — Request + UseCase in one file; map ORM → Result via `{Entity}Result(**orm.as_dict())`; pick the right `async with` pattern
7. `application/v1/usecases/__init__.py::setup_use_cases()` — register
8. `presentation/http/v1/contracts/` — request/response models; for list endpoints add `Select{Entities}` filter Contract
9. `presentation/http/v1/endpoints/<audience>/` — pick the audience folder; endpoint maps `Request` → `request_bus.send()` (or `request_bus.send_wrapped(wrapper, ...)` for cached/wrapped dispatch) → `OkResponse(contracts.X.model_validate(result))` (single) or `OkResponse(result.map(contracts.X.model_validate))` (list)
10. `tests/` — unit + integration + e2e

For consumers / scheduled tasks, replace step 8-9 with a subscriber/task wrapper in `consumers/` or `tasks/`.

## Code style — comments and docstrings

**Do not add docstrings, inline comments, or explanatory prose unless the logic is genuinely non-obvious.** The codebase is self-documenting through naming, types, and small focused functions. Noise makes diffs harder to review and signals that the code can't stand on its own.

**Forbidden by default:**
- Function-level docstrings on helpers, fixtures, test functions, short methods — the name and signature already carry the information.
- Class-level docstrings unless the class has non-obvious semantics that can't be inferred from its fields.
- Inline `# this does X` comments that restate the next line.
- Section dividers like `# === setup ===`, `# --- helpers ---`.
- Explanatory prose on config lines, fixtures, conftest entries, one-liners.
- "Why" comments that are actually "what" comments dressed up.

**Acceptable:**
- A non-obvious *reason* (an incident, a workaround, a spec quirk, a production bug that motivated the code).
- A surprising API used in a surprising way where a future reader would otherwise waste time.
- A load-bearing constant whose value comes from an external source (RFC number, vendor quirk, regulatory requirement).

**Rule of thumb:** when in doubt, leave it out. If a reviewer would delete the comment, don't write it. If the code can't speak for itself, rewrite the code — don't annotate it.

## Tech stack

Python 3.12+, FastAPI + Granian, SQLAlchemy 2.0 (async) + asyncpg + Alembic, Dishka (DI), Pydantic v2, Redis, NATS (nats-py + FastStream + Taskiq for cron), PyJWT + Argon2 + AES, aiohttp, orjson, msgpack, Ruff + MyPy (strict).
