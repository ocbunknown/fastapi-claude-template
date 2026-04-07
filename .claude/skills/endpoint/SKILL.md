---
name: endpoint
description: Use when creating or editing a FastAPI endpoint under src/presentation/http/v1/endpoints/<audience>/. Enforces audience-first organization (public/user/admin/internal), the exact parameter-naming convention (data for bodies, query for GET filters), the five-parameter list shape, correct Require + Authorization wiring, and strict contract ↔ Result mapping.
---

# Writing HTTP endpoints (`src/presentation/http/v1/endpoints/<audience>/`)

Endpoints are **thin adapters**. They have no business logic, no DB access, no validation beyond schema parsing. Their job is `contract → Request → request_bus.send() → OkResponse(contract.from(result))`.

## Pick the audience folder first

Endpoints live under `presentation/http/v1/endpoints/<audience>/` where `<audience>` decides auth:

| Folder | Router guard | Use for |
|---|---|---|
| `public/` | none | healthcheck, register, login, refresh, public forms |
| `user/` | `Authorization()` (any authenticated user) | `/users/me`, logout, anything user-owned |
| `admin/` | `Authorization("Admin")` | admin user management, moderation, cross-user operations |
| `internal/` | service-to-service stub, `include_in_schema=False` | webhooks, internal APIs |

**You never attach `Authorization(...)` at the endpoint function level** when the router already enforces it. FastAPI caches the dependency result per request, so declaring `user: Annotated[UserResult, Require(Authorization())]` as a parameter inside a `user/`-audience endpoint is free — it returns the same cached `UserResult` that the router-level guard already validated.

## Endpoint file skeleton

```python
# src/presentation/http/v1/endpoints/admin/widget.py
from typing import Annotated

import uuid_utils.compat as uuid
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status
from fastapi import Depends as Require

from src.application.common.interfaces.request_bus import RequestBus
from src.application.common.pagination import OffsetPagination
from src.application.v1.results import OffsetResult, WidgetResult
from src.application.v1.usecases.widget import (
    CreateWidgetRequest,
    SelectManyWidgetRequest,
    SelectWidgetRequest,
    UpdateWidgetRequest,
)
from src.common.di import Depends
from src.database.psql.types.widget import WidgetLoads
from src.presentation.http.common.responses import OkResponse
from src.presentation.http.v1 import contracts

admin_widget_router = APIRouter(
    prefix="/widgets", tags=["Admin | Widget"], route_class=DishkaRoute
)
```

### Fixed imports

- `from fastapi import Depends as Require` — the project **always** aliases `Depends` → `Require` to make the intent obvious.
- `from src.common.di import Depends` — this is **Dishka's** `Depends[T]` marker used for DI, different from FastAPI's `Depends`. Use `Depends[RequestBus]` etc. as parameter annotations.
- `from dishka.integrations.fastapi import DishkaRoute` — every `APIRouter` passes `route_class=DishkaRoute` so Dishka can inject into endpoints.
- `tags=["<Audience> | <Resource>"]` — two-word tag with a pipe, e.g. `"Admin | User"`, `"Admin | Widget"`, `"User"`, `"Public"`.

## Result → Contract mapping

Endpoints always hand the client a `Contract`, never a raw `Result`. There are two shapes:

- **Single item:** `contracts.User.model_validate(result)` — pass the Result instance directly. No `.model_dump()` round-trip needed; `Contract` inherits `from_attributes=True`, so Pydantic reads attributes off the Result object in place.
- **Paginated list:** `result.map(contracts.User.model_validate)` — `OffsetResult.map(fn)` applies `fn` to every item in `.data` and returns a new `OffsetResult[R]` with the same `offset/limit/total`. No manual unpacking, no re-building the envelope.

The `OffsetResult[T]` envelope is layer-agnostic — defined once in `application/v1/results/base.py` and reused as both the use case return type and the HTTP response type. You use the **application** class for `response_model=OffsetResult[contracts.User]`. There is no `contracts.OffsetResult`.

## Parameter naming — non-negotiable

| HTTP method | Input source | Parameter name | Type annotation |
|---|---|---|---|
| `GET` | query string filters | `query` | `Annotated[contracts.SelectWidgets, Require(contracts.SelectWidgets)]` |
| `POST`/`PATCH`/`PUT`/`DELETE` | JSON body | `data` | `contracts.CreateWidget` (direct, FastAPI parses body automatically) |
| path | path params | `widget_uuid: uuid.UUID` (literal FastAPI path) | — |
| extras for GET | standalone primitives | named (`loads`, `order_by`) | `tuple[WidgetLoads, ...] = Query(default=(), title="...")` |

**Never use** `body`, `payload`, `params`, `queries`, `input`, `args`. The project is consistent — `query` for GET filters, `data` for mutation bodies.

## The five-parameter list shape (`GET /widgets`)

Every list endpoint uses **exactly** this shape — do not deviate, do not reorder:

```python
@admin_widget_router.get(
    "",
    response_model=OffsetResult[contracts.Widget],
    status_code=status.HTTP_200_OK,
)
async def select_widgets_endpoint(
    request_bus: Depends[RequestBus],
    query: Annotated[contracts.SelectWidgets, Require(contracts.SelectWidgets)],
    pagination: Annotated[
        contracts.OffsetPagination, Require(contracts.OffsetPagination)
    ],
    loads: tuple[WidgetLoads, ...] = Query(
        default=(), title="Additional relations"
    ),
) -> OkResponse[OffsetResult[contracts.Widget]]:
    result: OffsetResult[WidgetResult] = await request_bus.send(
        SelectManyWidgetRequest(
            loads=loads,
            **query.model_dump(),
            pagination=OffsetPagination(**pagination.model_dump()),
        )
    )
    return OkResponse(result.map(contracts.Widget.model_validate))
```

Five things to notice:

1. **`query: Annotated[ContractCls, Require(ContractCls)]`** — `Require(ContractCls)` tells FastAPI to treat the Pydantic model's fields as **separate query string parameters**. This works for flat primitives (`str | None`, `UUID | None`, `int`, `Literal[...]`). Nested/complex types break — keep filter contracts flat.
2. **`pagination: Annotated[contracts.OffsetPagination, Require(contracts.OffsetPagination)]`** — same trick for pagination params. `contracts.OffsetPagination` is the **strict** version (`10 ≤ limit ≤ 200`, `offset ≥ 0`). It is **mapped** to the lenient application version on the request_bus.send line: `OffsetPagination(**pagination.model_dump())`. In the endpoint module the **unqualified** `OffsetPagination` refers to the application class (imported from `src.application.common.pagination`), and `contracts.OffsetPagination` refers to the strict HTTP contract class — no name collision.
3. **`loads: tuple[WidgetLoads, ...] = Query(default=(), title="...")`** — a **separate** standalone query parameter, not nested inside the filter contract. Lets the frontend opt in to relations per request. Forward as-is to the Request.
4. **`await request_bus.send(SelectManyWidgetRequest(loads=loads, **query.model_dump(), pagination=OffsetPagination(**pagination.model_dump())))`** — flat kwargs from the query contract, pagination mapped, loads forwarded.
5. **`result.map(contracts.Widget.model_validate)`** — the generic envelope `.map()` retargets the item type without re-building offset/limit/total manually. `contracts.Widget.model_validate(widget_result)` works because `Contract` uses `from_attributes=True`.

## Single `GET` / `PATCH` / `POST` shapes

### GET one (path param)

```python
@admin_widget_router.get(
    "/{widget_uuid}",
    response_model=contracts.Widget,
    status_code=status.HTTP_200_OK,
)
async def select_widget_endpoint(
    widget_uuid: uuid.UUID,
    request_bus: Depends[RequestBus],
    loads: tuple[WidgetLoads, ...] = Query(
        default=(), title="Additional relations"
    ),
) -> OkResponse[contracts.Widget]:
    result: WidgetResult = await request_bus.send(
        SelectWidgetRequest(widget_uuid=widget_uuid, loads=loads)
    )
    return OkResponse(contracts.Widget.model_validate(result))
```

### POST body

```python
@admin_widget_router.post(
    "",
    response_model=contracts.Widget,
    status_code=status.HTTP_201_CREATED,
)
async def create_widget_endpoint(
    data: contracts.CreateWidget,
    request_bus: Depends[RequestBus],
) -> OkResponse[contracts.Widget]:
    result: WidgetResult = await request_bus.send(
        CreateWidgetRequest(**data.model_dump())
    )
    return OkResponse(contracts.Widget.model_validate(result))
```

### PATCH with path + body

```python
@admin_widget_router.patch(
    "/{widget_uuid}",
    response_model=contracts.Widget,
    status_code=status.HTTP_200_OK,
)
async def update_widget_endpoint(
    widget_uuid: uuid.UUID,
    data: contracts.AdminUpdateWidget,
    request_bus: Depends[RequestBus],
) -> OkResponse[contracts.Widget]:
    result: WidgetResult = await request_bus.send(
        UpdateWidgetRequest(
            widget_uuid=widget_uuid,
            **data.model_dump(exclude_unset=True),
        )
    )
    return OkResponse(contracts.Widget.model_validate(result))
```

Note `exclude_unset=True` — PATCH bodies should forward only the fields the client actually sent, so the use case can distinguish "not provided" from "set to null".

## User-scoped endpoint (`/me`) — identity comes from the guard, never the client

When the endpoint lives under `user/` audience and operates on **the caller's own data**, the target identifier **must** come from the authenticated `user` parameter, never from the path or body:

```python
@user_me_router.patch(
    "",
    response_model=contracts.User,
    status_code=status.HTTP_200_OK,
)
async def update_self_endpoint(
    data: contracts.UpdateSelf,                              # ← NO role_uuid, NO active, NO user_uuid
    request_bus: Depends[RequestBus],
    user: Annotated[UserResult, Require(Authorization())],   # ← identity from JWT
) -> OkResponse[contracts.User]:
    result: UserResult = await request_bus.send(
        UpdateUserRequest(
            user_uuid=user.uuid,                              # ← from guard, never from client
            **data.model_dump(exclude_unset=True),
        )
    )
    return OkResponse(contracts.User.model_validate(result))
```

This is a **hard rule** — the architecture reviewer will fail any user endpoint that accepts an identifier in the path/body when the guard already provides it.

## Contract rules — the split between user and admin

For every mutation with a user-facing version and an admin-facing version, you need **two** separate contracts:

```python
# presentation/http/v1/contracts/widget.py

class UpdateSelfWidget(Contract):
    """Fields a user may change about their own widget."""
    name: str | None = None

class AdminUpdateWidget(Contract):
    """Fields an admin may change about any widget."""
    name: str | None = None
    owner_uuid: uuid.UUID | None = None    # privileged: reassign ownership
    active: bool | None = None              # privileged: moderation
```

**Privileged fields that must NEVER appear in a user contract:**

- `role_uuid`, `role`, `is_admin`, `permissions`, `scopes`
- `active`, `banned`, `email_verified`
- `user_uuid`, `target_uuid`, `id` (identity is from the guard, not the payload)
- `login`, `email` (identity fields)
- `quota`, `tier`, `plan` (billing-controlled)

**Fields that must NEVER appear in a response contract (any audience):**

- `password`, `password_hash`, `hashed_password`, `salt`
- `refresh_token`, `access_token` (unless you're returning a freshly issued pair in login/refresh)
- `secret`, `api_key`, `private_key`
- `stripe_customer_id`, `internal_note`
- Any column from a DB model that you'd be uncomfortable seeing in a server log

If the `Result` type includes such a field, that's fine (application layer can have rich data) — but the `Contract` is the filter. List only the fields the client is allowed to see.

## Router wiring (the `__init__.py`)

Each audience folder has a `__init__.py` that composes its endpoint files into a router with audience-level auth:

```python
# src/presentation/http/v1/endpoints/admin/__init__.py
from fastapi import APIRouter
from fastapi import Depends as Require

from src.presentation.http.v1.guards import Authorization

from .user import admin_user_router
from .widget import admin_widget_router


def setup_admin_router() -> APIRouter:
    router = APIRouter(
        prefix="/admin",
        dependencies=[Require(Authorization("Admin"))],
    )
    router.include_router(admin_user_router)
    router.include_router(admin_widget_router)
    return router
```

Then register the setup function in `src/presentation/http/v1/endpoints/__init__.py::setup_v1_routers()`.

## Anti-patterns (hard no)

- ❌ Business logic inside an endpoint (`if user.role.name == "Admin": ...`, DB calls, conditional mediation). Push it into a use case.
- ❌ Using `body`, `payload`, `params`, `queries` as parameter names. It's `data` for bodies, `query` for GET filters.
- ❌ `Authorization("Admin")` inside an endpoint parameter when the router already declares it. It double-validates the JWT.
- ❌ `Authorization()` (no role) in an `admin/` endpoint when the user must be `Admin`. The router should enforce `"Admin"`.
- ❌ Declaring a path parameter like `/users/{user_uuid}` under `user/` audience — users shouldn't target themselves via path, use `/users/me` or `/me`.
- ❌ Accepting `role_uuid`, `active`, `is_admin` in an `UpdateSelf*` contract.
- ❌ Returning a raw `Result` from the use case — always wrap in `OkResponse(contracts.X.model_validate(result))` (the intermediate `.model_dump()` is unnecessary because `Contract` sets `from_attributes=True`), or use `result.map(contracts.X.model_validate)` for `OffsetResult`.
- ❌ Forgetting `route_class=DishkaRoute` on `APIRouter(...)`. Without it, Dishka can't inject into endpoint parameters.
- ❌ Hard-coding `limit=10` or any pagination behavior in the endpoint — pagination lives in `contracts.OffsetPagination`.
- ❌ Calling the contract's `OffsetPagination` as `pagination: OffsetPagination = OffsetPagination()` — that's the application version. The endpoint must use `contracts.OffsetPagination` via `Require`.
