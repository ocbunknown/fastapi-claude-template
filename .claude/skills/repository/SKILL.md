---
name: repository
description: Use when creating or extending a repository under src/database/psql/repositories/. Enforces the project's fixed repository vocabulary (create, select, select_many, update, delete, exists, count, upsert) — no invented methods. Shows exactly how to wrap CRUDRepository, use @on_integrity, build loads-aware selects, and return Result[T].
---

# Writing repositories (`src/database/psql/repositories/`)

Repositories are **thin wrappers around `CRUDRepository`** that add domain semantics (named arguments, `loads`, ordering, `@on_integrity` for unique constraints). The CRUD verbs are fixed — do **not** invent new method names.

## Allowed method vocabulary — memorize this list

A repository may expose **only** these verbs (one per responsibility):

| Method | Purpose | Return |
|---|---|---|
| `create(**data)` | insert one row | `Result[M]` |
| `select(*loads, **filters)` | fetch one row by identifier(s) | `Result[M]` |
| `select_many(*loads, **filters, order_by, offset, limit)` | paginated list | `Result[tuple[int, Sequence[M]]]` |
| `update(uuid, /, **data)` | update one row by id | `Result[M]` |
| `delete(**filters)` | delete one row by id | `Result[M]` |
| `exists(**filters)` | existence check | `Result[bool]` |
| `count(**filters)` | count matching rows | `Result[int]` |
| `upsert(*conflict_cols, **data)` | insert-or-update on conflict | `Result[M]` |

**Do not invent** verbs like `get`, `fetch`, `find_one`, `find_by_email`, `list_all`, `save`, `remove`, `get_or_create`, `paginate`, `search`. If you need "find user by email", that's still `select(login=...)` with a new named parameter. If the current method doesn't support a filter you need, **add a new keyword arg** to the existing method — do not add a new method.

The only acceptable additions beyond this vocabulary are domain-specific **bulk variants** that mirror CRUD (`insert_many` on CRUDRepository already exists — use it via `self._crud.insert_many(...)`).

## Anatomy of a repository

Every repository inherits `BaseRepository[models.X]` and accesses CRUD primitives through `self._crud`:

```python
# src/database/psql/repositories/widget.py
from collections.abc import Sequence
from typing import Optional, Unpack

import uuid_utils.compat as uuid
from sqlalchemy import ColumnExpressionArgument

import src.database.psql.models as models
from src.database.psql.exceptions import InvalidParamsError
from src.database.psql.repositories import Result
from src.database.psql.repositories.base import BaseRepository
from src.database.psql.tools import (
    on_integrity,
    sqla_offset_query,
    sqla_select,
    unique_scalars,
)
from src.database.psql.types import OrderBy
from src.database.psql.types.widget import (
    CreateWidgetType,
    UpdateWidgetType,
    WidgetLoads,
)


class WidgetRepository(BaseRepository[models.Widget]):
    __slots__ = ()

    @on_integrity("name")
    async def create(self, **data: Unpack[CreateWidgetType]) -> Result[models.Widget]:
        return Result("create", await self._crud.insert(**data))

    async def select(
        self,
        *loads: WidgetLoads,
        widget_uuid: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
    ) -> Result[models.Widget]:
        if not any([widget_uuid, name]):
            raise InvalidParamsError("at least one identifier must be provided")

        where_clauses: list[ColumnExpressionArgument[bool]] = []
        if widget_uuid:
            where_clauses.append(self.model.uuid == widget_uuid)
        if name:
            where_clauses.append(self.model.name == name)

        stmt = sqla_select(model=self.model, loads=loads).where(*where_clauses)
        return Result(
            "select", unique_scalars(await self._session.execute(stmt)).first()
        )

    @on_integrity("name")
    async def update(
        self,
        uuid: uuid.UUID,
        /,
        **data: Unpack[UpdateWidgetType],
    ) -> Result[models.Widget]:
        result = await self._crud.update(self.model.uuid == uuid, **data)
        return Result("update", result[0] if result else None)

    async def delete(
        self, widget_uuid: Optional[uuid.UUID] = None
    ) -> Result[models.Widget]:
        if not widget_uuid:
            raise InvalidParamsError("at least one identifier must be provided")

        result = await self._crud.delete(self.model.uuid == widget_uuid)
        return Result("delete", result[0] if result else None)

    async def select_many(
        self,
        *loads: WidgetLoads,
        name: Optional[str] = None,
        order_by: OrderBy = "desc",
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> Result[tuple[int, Sequence[models.Widget]]]:
        where_clauses: list[ColumnExpressionArgument[bool]] = []

        if name:
            where_clauses.append(self.model.name.ilike(f"%{name}%"))

        total = await self._crud.count(*where_clauses)
        if total <= 0:
            return Result("select", (total, []))

        stmt = sqla_offset_query(
            self.model,
            loads=loads,
            offset=offset,
            limit=limit,
            order=("created_at", order_by),
            where=where_clauses,
        )
        results = unique_scalars(await self._session.execute(stmt)).all()
        return Result("select", (total, results))

    async def exists(self, name: str) -> Result[bool]:
        return Result("exists", await self._crud.exists(self.model.name == name))
```

## Fixed rules

1. **Always return `Result[T]`** from every public method. The first argument to `Result(...)` is the exception key (`"create" | "select" | "select_many" | "update" | "delete" | "exists" | "count" | "upsert"`) — it determines which domain exception `result.result()` raises on `None`.
2. **Always use `sqla_select(model=..., loads=loads)`** for single-row reads with eager loading and **`sqla_offset_query(model, loads=loads, offset=..., limit=..., order=(col, dir), where=...)`** for paginated reads. Both come from `src.database.psql.tools` (re-exported from `sqla-autoloads`). Never write raw `select(...).options(selectinload(...))` in a repository, and never apply `.limit()/.offset()` directly to a `sqla_select` query — the library helper handles pagination correctly via a CTE on the primary key so eager-loading joins operate only on the page slice.
3. **Always materialise results via `unique_scalars(...)`** (also re-exported from `src.database.psql.tools`). It returns a `ScalarResult` so you can chain `.first()` for single rows or `.all()` for collections. This deduplicates rows produced by outer-join eager loading — never call `.unique().scalars()` by hand.
4. **Always decorate `create` / `update` / `upsert` with `@on_integrity("unique_col_1", "unique_col_2")`** if the model has unique constraints. This converts SQLAlchemy `IntegrityError` into `ConflictError("<col> already in use")`.
5. **`select_many` must honour `limit: Optional[int] = None`** — no upper cap, no default limit. The cap is enforced at the contract layer (`presentation/http/v1/contracts/pagination.py` — 200 max). Internal callers (use cases, tasks) can pass `limit=None` for "all rows". `select_many` also returns `(total, rows)` — total is always computed via `self._crud.count(*where_clauses)` **before** the rows query, and if `total <= 0` return early with an empty sequence.
6. **Raise `InvalidParamsError` when no identifier is provided** on `select` / `delete` / `update` with optional filters — mirrors `UserRepository` / `RoleRepository`.
7. **`__slots__ = ()`** on every repository subclass.
8. **Filter arg names are specific**: `widget_uuid` not `id`, `login` not `email`, `role_uuid` not `role`. The `uuid_utils.compat.UUID` type is imported as `import uuid_utils.compat as uuid` and typed as `uuid.UUID`.

## sqla-autoloads helpers

`src/database/psql/tools.py` re-exports the library's query API so repositories never import from `sqla_autoloads` directly:

| Helper | Use for |
|---|---|
| `sqla_select(model=..., loads=...)` | single-row reads with eager loading; chain `.where(...)` for filters |
| `sqla_offset_query(model, *, loads, offset, limit, order=(col, dir), where=[...])` | paginated list reads — builds a CTE on the PK so the page slice is computed before joins, avoiding row multiplication from eager loads |
| `sqla_cursor_query(model, *, loads, limit, after=None, before=None, order=(col, dir), where=[...])` | cursor-based pagination (forward via `after`, backward via `before`); fetches `limit + 1` rows so the caller can detect a next page |
| `unique_scalars(result)` | shorthand for `result.unique().scalars()`; returns a `ScalarResult` — chain `.first()` or `.all()` |
| `add_conditions(*exprs)` | build a per-relationship WHERE callable to pass into `sqla_select(conditions={...})` |

`order` is a `(column_name, "asc" | "desc")` tuple — pass `order=("created_at", order_by)` to sort by a domain column. `where` accepts the same `ColumnExpressionArgument[bool]` list that you would build by hand.

When pagination needs cursors (e.g. a feed), use `sqla_cursor_query` instead of `sqla_offset_query` and reverse the result list when `before` is set:

```python
stmt = sqla_cursor_query(
    self.model,
    loads=loads,
    limit=limit,
    after=after,
    order=("created_at", order_by),
    where=where_clauses,
)
rows = unique_scalars(await self._session.execute(stmt)).all()
has_next = len(rows) > limit
items = rows[:limit]
```

## Types & loads (required companion files)

For every new repository, add (or extend) `src/database/psql/types/<entity>.py`:

```python
from typing import Literal, TypedDict
from uuid_utils.compat import UUID

WidgetLoads = Literal["owner", "tags"]  # relationships the caller may eager-load

class CreateWidgetType(TypedDict):
    name: str
    owner_uuid: UUID

class UpdateWidgetType(TypedDict, total=False):
    name: str | None
    owner_uuid: UUID | None
```

`WidgetLoads` lists the relationship names (str literals) that `sqla_select` knows how to eager-load. Only include relationships that are actually defined on the model.

## Wire into `DBGateway`

After writing the repository and types, add a property on `src/database/psql/__init__.py::DBGateway`:

```python
@property
def widget(self) -> WidgetRepository:
    return self._from_cache("widget", WidgetRepository, model=models.Widget)
```

The `_from_cache` helper memoizes the instance per gateway (= per request scope), so multiple use cases in the same request share one repository/one session.

## Anti-patterns (hard no)

- ❌ Inventing new verb names (`find_by_name`, `list_active`, `bulk_create`, `save`, `remove`, `get_or_create`, `paginate`, `search`) — use existing CRUD verbs with new kwargs.
- ❌ Calling `self._session.execute(text(...))` or writing raw SQL strings inside a repository — use Query Objects under `database/psql/queries/` for complex SQL.
- ❌ Committing inside a repository method (`self._session.commit()`) — commits are owned by the `DBGateway` context manager.
- ❌ Returning a bare ORM model (`-> models.Widget`) instead of `Result[models.Widget]`.
- ❌ Hardcoding a `limit` default in `select_many` (e.g. `limit: int = 10`) — must be `Optional[int] = None`. Default pagination lives in the contract layer.
- ❌ Calling `UserResult.model_validate(...)` inside a repository. Result types live in `application/` — repositories never construct them.
- ❌ Adding `flush` / `refresh` / `expire` calls — the transaction manager handles that.
- ❌ Importing from `src.application.*` (use case layer) or `src.presentation.*` / `src.infrastructure.*`. The only legal cross-layer import is `src.application.common.exceptions` (and only for exceptions).
