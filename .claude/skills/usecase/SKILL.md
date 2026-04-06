---
name: usecase
description: Use when creating or editing a use case under src/application/v1/usecases/. Enforces the Mediator + UseCase pattern (Request + UseCase in one file, @dataclass(slots=True), returns Result type) and the DBGateway transaction rules — never open two sessions in one use case, never touch self.database outside a context manager, never lazy-load relationships outside the session.
---

# Writing use cases (`src/application/v1/usecases/<domain>/`)

A use case is the **transport-agnostic unit of business logic**. Endpoints, consumers, and scheduled tasks all call `mediator.send(Request(...))` and get back a `Result`. Use cases never know who called them.

## One file, two classes

Every use case file defines **exactly one** `Request` class and **exactly one** `UseCase` class. Keep them in the same file — they are a pair.

```python
# src/application/v1/usecases/widget/create.py
from dataclasses import dataclass
from typing import Annotated

import uuid_utils.compat as uuid
from pydantic import Field

from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.results import WidgetResult
from src.database.psql import DBGateway


class CreateWidgetRequest(Request):
    name: Annotated[str, Field(max_length=64)]
    owner_uuid: uuid.UUID


@dataclass(slots=True)
class CreateWidgetUseCase(UseCase[CreateWidgetRequest, WidgetResult]):
    database: DBGateway

    async def __call__(self, request: CreateWidgetRequest) -> WidgetResult:
        async with self.database:
            widget = (
                await self.database.widget.create(
                    name=request.name,
                    owner_uuid=request.owner_uuid,
                )
            ).result()
            return WidgetResult(**widget.as_dict())
```

## Invariants

1. **`Request`** inherits `src.application.common.request.Request` (Pydantic, `frozen=True`). Validation via `Annotated[..., Field(...)]`. Do not reuse HTTP `Contract` classes here — the Request describes the use-case input, not the HTTP input.
2. **`UseCase`** inherits `UseCase[RequestClass, ReturnType]`. The base class auto-applies `@dataclass(slots=True)` — add your own `@dataclass(slots=True)` on the subclass too for mypy/readability.
3. **Dependencies are dataclass fields**: `database: DBGateway`, `hasher: Hasher`, `cache: StrCache`, `services: ServiceGateway`, etc. Injected by Dishka via the mediator — do not instantiate manually.
4. **Returns a `Result` subclass** from `src/application/v1/results/` — never a `Contract` from `presentation/`, never a bare ORM model, never a dict.
5. **Register** the use case in `src/application/v1/usecases/__init__.py::setup_use_cases()`:
   ```python
   mediator.register(widget.CreateWidgetRequest, widget.CreateWidgetUseCase)
   ```
6. **Re-export** from `src/application/v1/usecases/widget/__init__.py` so the presentation/consumers layer can import `from src.application.v1.usecases.widget import CreateWidgetRequest`.

## DBGateway — the transaction rule

This is the **single most common place people break production**. Read carefully.

`DBGateway` owns one session per request. It exposes two context managers. **You pick exactly one per use case — never both, never twice.**

### Pattern 1 — read-only

```python
async def __call__(self, request: SelectWidgetRequest) -> WidgetResult:
    async with self.database.manager.session:
        widget = (
            await self.database.widget.select(*request.loads, widget_uuid=request.widget_uuid)
        ).result()
        return WidgetResult(**widget.as_dict())
```

- Use for pure reads: one or many `select` / `exists` / `count` calls, no mutations.
- No transaction is opened — `session.begin()` is never called.
- Build the Result via `WidgetResult(**widget.as_dict())` — see "Mapping ORM → Result" below for why `.model_validate(widget)` is forbidden.
- Keep construction **inside** the `async with` block by convention — it localizes session-touching code and keeps the pattern consistent even when the use case later grows logic that genuinely needs the open session.

### Pattern 2 — write

```python
async def __call__(self, request: CreateWidgetRequest) -> WidgetResult:
    async with self.database:
        widget = (
            await self.database.widget.create(
                name=request.name,
                owner_uuid=request.owner_uuid,
            )
        ).result()
        return WidgetResult(**widget.as_dict())
```

- Use for any mutation (`create` / `update` / `delete` / `upsert`).
- `async with self.database:` calls `session.begin()` → autocommit on success, autorollback on exception.
- Every `self.database.X` call and every `Result` construction belongs **inside** this block.

### Pattern 3 — read then write (single transaction)

When a write needs data that was just read, put **both** in one `async with self.database:` block:

```python
async def __call__(self, request: ConfirmRegisterRequest) -> TokensExpire:
    cached_data = await self.cache.get(key)
    if not cached_data:
        raise NotFoundError("Code has expired or invalid")

    async with self.database:
        role = (await self.database.role.select(name="User")).result()       # read
        user = (
            await self.database.user.create(                                   # write
                login=cached_user.login,
                password=self.hasher.hash_password(cached_user.password),
                role_uuid=role.uuid,
            )
        ).result()

    return await self.services.auth.login(cached_user.fingerprint, user.uuid)
```

One session. One transaction. Both operations atomic.

### Anti-patterns (hook will not catch these — you must self-check)

| ❌ Anti-pattern | Why it breaks | ✅ Fix |
|---|---|---|
| Opening the session twice: one `async with self.database.manager.session:` for the read, then a second `async with self.database:` for the write | The session is single-use — second `async with` fails on a closed session | Combine both into a single `async with self.database:` block |
| Nesting `async with self.database:` and `async with self.database.manager.session:` | Double-entering the same session | Pick one — for writes, `async with self.database:` only |
| `WidgetResult.model_validate(widget)` where `widget` is an ORM row | Pydantic's `from_attributes=True` does `getattr(widget, "owner")`, which triggers SQLAlchemy lazy loading → `MissingGreenlet` on an async session | Use `WidgetResult(**widget.as_dict())` — `Base.as_dict()` iterates `__dict__`, which contains only already-loaded attributes; missing relationships fall back to the Pydantic field default (`None`) |
| Mutating inside `async with self.database.manager.session:` | No `session.begin()` → no commit → silent data loss | Switch to `async with self.database:` |
| Calling `self.database.widget.create(...)` **outside** any context | Session state undefined | Wrap in the appropriate context |
| Expecting a relationship to appear in the Result when the caller did not pass it in `loads` | `Base.as_dict()` skips unloaded relations, so the field ends up `None` — if your use case *depends* on the relation, the response is silently wrong | Either forward `*request.loads` to the repo call and document that the relation is optional in the Result, or add the relation to loads unconditionally inside the use case (rare — usually it's the caller's choice) |

**Rule of thumb**: when in doubt, use `async with self.database:`. It works for both reads and writes — worst case you pay for a transaction you didn't need. The other direction (using `manager.session` for a write) silently loses data.

## Mapping ORM → Result — use `Base.as_dict()`

Every ORM model inherits `Base.as_dict()` (defined in `src/database/psql/models/base/core.py`). **This is the only way you should build a Result from an ORM row.**

```python
# Single
return WidgetResult(**widget.as_dict())

# List (inside select_many use cases)
data=[WidgetResult(**w.as_dict()) for w in widgets]
```

### Why this works and `model_validate` doesn't

`Base.as_dict()` iterates `self.__dict__` directly. SQLAlchemy puts **only loaded attributes** in `__dict__`:

- Columns (`uuid`, `name`, `owner_uuid`, `created_at`, …) are populated at `SELECT` time → always present.
- Relationships (`owner`, `tags`, …) are populated **only** if the caller eager-loaded them via `loads=...`. Otherwise they're not in `__dict__` at all — they live on the class descriptor and would be fetched via lazy-load on `getattr`.

So `widget.as_dict()` never triggers a lazy load — it doesn't do `getattr`, it reads `__dict__` directly. Missing relationship → missing dict key → Pydantic falls back to the field default (`owner: OwnerResult | None = None`).

By contrast, `WidgetResult.model_validate(widget)` uses Pydantic's `from_attributes=True` mode, which walks the declared fields and calls `getattr(widget, "owner")` — that triggers SQLAlchemy's lazy load, which inside an async session crashes with `MissingGreenlet`. **Never do this for ORM rows.** (It's still fine for dicts, Results, and other non-ORM objects.)

### The load contract

The caller decides which relations appear in the response via `loads=...`:

- `loads=()` (default) → only columns; relationships come back as `None` and the HTTP serializer (`exclude_none=True` in `presentation/http/common/serializers/default.py`) drops them from the JSON entirely.
- `loads=("owner",)` → `as_dict()` finds `owner` in `__dict__` as a nested `Base`, recursively converts it to a dict, and Pydantic coerces the dict into `OwnerResult`.

Don't defensively check `inspect(orm).unloaded` in the use case. The load contract **is** the opt-in — honour it and let `as_dict()` do its thing.

### Extra ORM columns vs declared Result fields

`Base.as_dict()` returns every column in `__dict__`, including ones the Result doesn't declare (`password`, `created_at`, `updated_at`, `role_uuid`, …). Pydantic v2 defaults to `extra="ignore"`, so these silently drop during `WidgetResult(**widget.as_dict())`. No config needed.

## List (`select_many`) use cases — special shape

```python
from src.application.common.pagination import OffsetPagination
from src.application.v1.results import OffsetResult, WidgetResult


class SelectManyWidgetRequest(Request):
    loads: tuple[WidgetLoads, ...] = ()
    name: str | None = None
    pagination: OffsetPagination = OffsetPagination()


@dataclass(slots=True)
class SelectManyWidgetUseCase(
    UseCase[SelectManyWidgetRequest, OffsetResult[WidgetResult]]
):
    database: DBGateway

    async def __call__(
        self, request: SelectManyWidgetRequest
    ) -> OffsetResult[WidgetResult]:
        async with self.database.manager.session:
            total, widgets = (
                await self.database.widget.select_many(
                    *request.loads,
                    name=request.name,
                    **request.pagination.model_dump(),
                )
            ).result()

            return OffsetResult[WidgetResult](
                data=[WidgetResult(**w.as_dict()) for w in widgets],
                offset=request.pagination.offset,
                limit=request.pagination.limit,
                total=total,
            )
```

- `pagination: OffsetPagination = OffsetPagination()` — the **application** version (`src/application/common/pagination.py`), which allows `limit: int | None = None` (unbounded for internal callers).
- `**request.pagination.model_dump()` spreads `order_by`, `offset`, `limit` into the repo call.
- `WidgetResult(**w.as_dict())` — see "Mapping ORM → Result" above.
- Returns `OffsetResult[WidgetResult]` — the generic envelope with `.map()` so the endpoint can retarget item types.

## Anti-patterns (hard no)

- ❌ Importing anything from `src.infrastructure.*`, `src.presentation.*`, `src.consumers.*`, `src.tasks.*`. The layer hook will block this, but be aware anyway.
- ❌ Importing a `Contract` class from `presentation/` and returning it. Return `Result` types only.
- ❌ Calling `session.execute` directly — go through the repository.
- ❌ Writing two separate `async with` blocks on `self.database` in one use case.
- ❌ Adding business logic to a `Request` class. `Request` is a frozen Pydantic model — validation only.
- ❌ Registering a use case in `setup_use_cases()` but forgetting to re-export it from `usecases/<domain>/__init__.py`.
- ❌ Using `@dataclass` **without** `slots=True`. The base class auto-applies it, but being explicit keeps mypy happy.
