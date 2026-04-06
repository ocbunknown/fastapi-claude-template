# FastAPI Template

> Production-ready FastAPI template with Clean Architecture, multi-transport support (HTTP / NATS consumers / Taskiq scheduler), and first-class [Claude Code](https://claude.com/claude-code) integration — custom skills, architecture hooks, and a review agent that teach the AI how the codebase is structured.

A batteries-included starting point for building async Python services. Ships with the boring-but-important stuff already wired: Dishka DI across three transports, SQLAlchemy 2.0 async + Alembic, Pydantic v2 contracts, JWT auth, pagination, layered testing with `testcontainers`, and strict layer boundaries enforced by Claude Code hooks so the architecture stays clean as the project grows.

---

## Highlights

- **Clean Architecture + Hexagonal** — strict inward dependencies (`application/` → `database/` is the only documented exception). The full ruleset lives in [`CLAUDE.md`](./CLAUDE.md).
- **Three transports, one composition root** — HTTP (`FastAPI` + `Granian`), message consumers (`FastStream` over NATS), scheduled jobs (`Taskiq` over NATS JetStream). All share the same Dishka container built by `entrypoints/container.py`.
- **Mediator + UseCase pattern** — every transport translates input into a `Request`, calls `mediator.send()`, and unwraps a `Result`. Zero business logic in endpoints/subscribers/tasks.
- **Audience-first HTTP routing** — endpoints grouped by who can call them (`public/`, `user/`, `admin/`, `internal/`). Auth is wired once at the router level; it's structurally impossible to forget on individual endpoints.
- **Strict/lenient pagination split** — HTTP contract enforces `10 ≤ limit ≤ 200`; internal callers can request unbounded fetches via `limit=None`.
- **Layered testing** — unit (mocks only), integration (`testcontainers` Postgres/Redis/NATS), e2e (full HTTP stack via `httpx.AsyncClient` + `ASGITransport`).
- **Claude Code native** — custom skills for `usecase` / `endpoint` / `repository` / `migration`, pre-commit hooks that block layer violations and protected-path edits, an architecture review agent, and a 417-line `CLAUDE.md` that's the authoritative spec.

---

## Tech stack

| Area | Stack |
|---|---|
| Runtime | Python 3.12+, [uv](https://docs.astral.sh/uv/) for deps |
| Web | FastAPI 0.115+, Granian (Rust-based ASGI server) |
| DI | [Dishka](https://dishka.readthedocs.io/) — scoped IoC container, one source of truth across HTTP / consumers / tasks |
| DB | SQLAlchemy 2.0 (async) + asyncpg, Alembic migrations |
| Validation | Pydantic v2 (frozen Request models, strict Contract models) |
| Cache | Redis (`redis.asyncio`) |
| Messaging | NATS (`nats-py`, FastStream for subscribers, Taskiq-NATS for cron jobs) |
| Security | PyJWT (HS256/RS256), Argon2 password hashing, AES for sensitive fields |
| Serialization | orjson (HTTP), msgpack (broker payloads) |
| Tooling | Ruff + MyPy (strict), pytest + pytest-xdist + testcontainers |

---

## Quick start

### 1. Install dependencies

```bash
uv sync
```

### 2. Start dependencies (Postgres, Redis, NATS)

```bash
make docker_dev_up
```

### 3. Configure `.env`

Copy the example settings and fill in cipher keys / DB credentials (see `src/settings/core.py` for all fields):

```bash
cp .env.example .env   # if you have one; otherwise create .env manually
```

Required keys: `DB_*`, `REDIS_*`, `NATS_*`, `CIPHER_*` (algorithm + secret_key + token TTLs).

### 4. Run migrations

```bash
make upgrade
```

### 5. Start the services

```bash
# HTTP API (FastAPI + Granian)
uv run python -m src

# Message consumer (FastStream over NATS)
uv run faststream run src.entrypoints.consumer:app

# Scheduler (Taskiq)
uv run taskiq worker src.entrypoints.scheduler:broker
uv run taskiq scheduler src.entrypoints.scheduler:scheduler
```

Each transport has its own entry point under `src/entrypoints/` and all three share the same Dishka container built by `entrypoints/container.py::build_container(settings, *extras)`.

---

## Project layout

```
src/
├── application/       USE CASES — transport-agnostic business logic
│   ├── common/        ports (Hasher, Cache, JWT, EventBus, Broker), mediator, exceptions, Request base, OffsetPagination
│   └── v1/            usecases, services, results, events, constants
│
├── infrastructure/    OUTBOUND ADAPTERS — Redis, Argon2, PyJWT, aiohttp, NATS brokers, logging
│
├── database/          PERSISTENCE — first-class layer (shared kernel)
│   ├── models/        SQLAlchemy ORM (inherit Base with .as_dict())
│   ├── repositories/  create/select/select_many/update/delete/exists/count/upsert — fixed vocabulary
│   ├── queries/       Query Object pattern for complex SQL
│   └── types/         OrderBy, Loads literals, TypedDict payloads
│
├── presentation/      INBOUND ADAPTER — FastAPI HTTP
│   └── http/v1/
│       ├── contracts/     Pydantic request/response schemas + strict OffsetPagination
│       ├── guards/        Authorization (JWT + role check)
│       └── endpoints/     audience-first: public/, user/, admin/, internal/
│
├── consumers/         INBOUND ADAPTER — FastStream (NATS subscribers)
├── tasks/             INBOUND ADAPTER — Taskiq (scheduled jobs)
│
├── entrypoints/       composition root: http.py, consumer.py, scheduler.py, container.py
├── common/            leaf utilities (Dishka helpers, formatters, types)
└── settings/          Pydantic Settings
```

See [`CLAUDE.md`](./CLAUDE.md) for the full architecture spec — layer rules, DBGateway patterns, list endpoint shape, ORM→Result mapping, naming conventions.

---

## Testing

Three layers, marked and parallelized via `pytest-xdist`:

```bash
uv run pytest tests/unit/           # no I/O, mocks/fakes only (~1s)
uv run pytest tests/integration/    # real Postgres/Redis/NATS via testcontainers
uv run pytest tests/e2e/            # full HTTP stack via httpx.AsyncClient + ASGITransport
uv run pytest                       # all of the above
```

Test infrastructure notes:
- `tests/conftest.py` spins up containers once per session, runs Alembic migrations in a sync context (migration env uses `asyncio.run` internally), creates a per-worker DB for xdist isolation.
- Each test runs inside an outer transaction that's rolled back on teardown — state stays clean with no explicit reset.
- E2E tests use `httpx.AsyncClient` + `httpx.ASGITransport` (not `TestClient`) to keep asyncpg connections on the same event loop as the app, avoiding the classic "attached to a different loop" trap.

---

## Claude Code integration

This template is designed to be developed **with** an AI assistant, not in spite of one. The `.claude/` directory ships opinionated configuration so Claude Code understands the codebase rules, enforces them automatically, and can scaffold new features consistently.

### Skills (`.claude/skills/`)

Custom skills that kick in when Claude is working on a specific kind of file. Each skill is a self-contained `SKILL.md` with examples, anti-patterns, and checklists.

| Skill | Triggers when… | Enforces |
|---|---|---|
| **`usecase`** | editing `src/application/v1/usecases/` | Mediator + UseCase pattern, `@dataclass(slots=True)`, `Request` in the same file, `DBGateway` transaction rules (pattern 1/2/3), `{Entity}Result(**orm.as_dict())` over `model_validate(orm)`, the list-endpoint shape for `select_many` use cases |
| **`endpoint`** | editing `src/presentation/http/v1/endpoints/<audience>/` | audience-first organization, the **five-parameter list shape** (`mediator / query / pagination / loads / return`), parameter naming (`query` for GET filters, `data` for POST/PATCH/PUT bodies), strict contract ↔ Result mapping, privileged-field lockdown between `UpdateSelf` vs `AdminUpdateX` contracts |
| **`repository`** | editing `src/database/psql/repositories/` | the fixed CRUD verb vocabulary (`create`, `select`, `select_many`, `update`, `delete`, `exists`, `count`, `upsert` — no invented names like `find_one` or `save`), `@on_integrity` for unique constraints, `sqla_select` for eager loading, `Result[T]` return wrapping, `limit: Optional[int] = None` for unbounded internal callers |
| **`migration`** | adding/changing schema | migrations are generated via `make generate NAME=...`, never hand-written; existing files in `migrations/versions/` are immutable history; data migrations + enum additions need manual `op.execute` |

### Hooks (`.claude/hooks/`)

Runtime guards that execute on every tool call. Claude is blocked *before* it can make an architectural or safety mistake.

| Hook | Event | What it does |
|---|---|---|
| **`guard_layers.py`** | `PreToolUse` on `Edit/Write/MultiEdit` | Parses the new file content and blocks imports that would violate the layer dependency rules (e.g. `application/` importing `infrastructure/`, `presentation/` importing `consumers/`). The documented `application → database` exception is allowed. |
| **`guard_paths.py`** | `PreToolUse` on `Edit/Write/MultiEdit` | Blocks edits to protected files: committed Alembic migrations (`migrations/versions/NN_*.py`), `migrations/env.py`, lockfiles (`uv.lock`), `.env*` secrets, `pyproject.toml`. Forces Claude to go through proper tooling (`make generate`, `uv add`). |
| **`pre_commit_checks.py`** | `PreToolUse` on `Bash` when command matches `git commit` | Runs `ruff check` + `mypy --strict` on `src/` and `tests/` before allowing the commit. Failed checks block the commit with the errors printed back to Claude to fix. |
| **`ruff_fix.py`** | `PostToolUse` on `Edit/Write/MultiEdit` | Silently runs `ruff format` + `ruff check --fix` on the edited Python file. Keeps formatting consistent without cluttering Claude's context. |

Hooks live in `.claude/settings.json` — the repo-committed config. No machine-specific state.

### Agents (`.claude/agents/`)

| Agent | Purpose |
|---|---|
| **`architecture-reviewer`** | On-demand architecture & authorization reviewer. Reads `CLAUDE.md`, walks git diff or specified files, flags layer violations, DBGateway misuse, privileged fields leaking into user contracts, missing role checks, and response-body leaks. Produces a structured Critical/Architecture/Advisory report. Never modifies files. |

### `CLAUDE.md`

The authoritative project spec that Claude Code reads as part of its context on every session. It documents:

- Layer dependency rules (with table and diagram)
- The `database/` exception and when it applies
- `DBGateway` usage rules with the three canonical patterns (read / write / read-then-write) and the anti-pattern table
- `Base.as_dict()` vs `model_validate(orm)` — the lazy-load footgun explained
- Audience-first HTTP endpoint organization
- The **five-parameter list endpoint shape** with pagination, filter contracts, and `loads`
- Strict vs lenient `OffsetPagination` split (presentation vs application)
- `OffsetResult.map()` for Result → Contract conversion
- Mediator + UseCase + Request + Result rules
- Naming conventions (single vs list, GET `query` vs POST `data`, OpenAPI tags)
- Adding-a-new-feature checklist

If a rule isn't in `CLAUDE.md`, it isn't a rule.

---

## Makefile targets

```bash
make upgrade                       # alembic upgrade head
make downgrade                     # alembic downgrade -1
make generate NAME="add_widget"    # alembic revision --autogenerate

make docker_dev_up                 # start dev containers (Postgres, Redis, NATS)
make docker_dev_down               # stop them
make docker_dev_rebuild            # down + build --no-cache
```

---

## Adding a new feature

The canonical walkthrough is in [`CLAUDE.md`](./CLAUDE.md#adding-a-new-feature--checklist). Summary:

1. **Model** — add to `database/models/`, run `make generate NAME="add_widget"`, inspect the migration
2. **Types** — `Create{Entity}Type`, `Update{Entity}Type`, `{Entity}Loads` in `database/types/`
3. **Repository** — wrap `BaseRepository`, add verbs from the fixed vocabulary, return `Result[T]`
4. **Gateway** — add a property on `DBGateway` in `database/psql/__init__.py`
5. **Result** — `{Entity}Result(Result)` in `application/v1/results/`
6. **Use case** — `Request + UseCase` in one file under `application/v1/usecases/{domain}/`; map ORM → Result via `{Entity}Result(**orm.as_dict())`
7. **Register** — add to `application/v1/usecases/__init__.py::setup_use_cases()`
8. **Contract** — Pydantic request/response in `presentation/http/v1/contracts/`
9. **Endpoint** — pick the audience folder, follow the five-parameter shape for lists
10. **Tests** — unit + integration + e2e

If you're using Claude Code, the `usecase` / `endpoint` / `repository` / `migration` skills will walk you through each step with the exact patterns.

---

## License

MIT (or whatever you prefer — update this section before publishing).
