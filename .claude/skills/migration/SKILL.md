---
name: migration
description: Use when the user asks to create a database migration, change a SQLAlchemy model, add a column, add an index, or otherwise modify the schema. Enforces the rule that migrations are generated via `make generate NAME="..."` (the project's Makefile target that runs Alembic autogenerate) — never hand-written — and never edit existing migration files in migrations/versions/.
---

# Creating database migrations

Migrations in this project are generated via the **Makefile**, which wraps Alembic's autogenerate. You never write migration files by hand, and you never edit an existing migration file.

## The three Makefile targets

```makefile
upgrade:    alembic upgrade head                # apply all pending migrations
downgrade:  alembic downgrade -1                # roll back the latest migration
generate:   alembic revision --autogenerate -m "$(NAME)"   # create a new migration
```

Run them from the repo root. The generate target requires a `NAME` variable — Alembic uses it as the migration message (and as part of the filename slug).

## The standard workflow

When the user asks for a schema change, follow **this exact order**:

1. **Edit the SQLAlchemy model** under `src/database/psql/models/<entity>.py`. Add/remove columns, indices, constraints, relationships — whatever the request needs.
2. **Update companion types** under `src/database/psql/types/<entity>.py`:
   - If a new writable column: add it to `Create<Entity>Type` (required) and/or `Update<Entity>Type` (optional, `total=False`).
   - If a new relationship: add its name to `<Entity>Loads = Literal[...]`.
3. **Generate the migration** via the Makefile — do **not** call `alembic` directly:
   ```bash
   make generate NAME="add_is_verified_to_user"
   ```
   Alembic autogenerate will diff the model metadata against the current DB schema and write a new file to `migrations/versions/NN_<hash>_add_is_verified_to_user.py`. The `NN_` numeric prefix is added by the project's naming convention — Alembic appends the hash + slug.
4. **Inspect the generated file.** Autogenerate is imperfect — it often misses:
   - Column type changes (e.g. `String(32)` → `String(64)` may require manual `alter_column` with `existing_type`)
   - Index renames
   - Enum value additions (Postgres `ALTER TYPE ... ADD VALUE`)
   - `server_default` changes
   - Data migrations (filling a new NOT NULL column for existing rows)

   Open the generated file and verify the `upgrade()` and `downgrade()` functions match your intent. If anything is missing or wrong, **edit the generated file now** — it is fresh, uncommitted, not yet applied. Once a migration is applied to dev/staging/prod, it becomes immutable.
5. **Apply it locally**:
   ```bash
   make upgrade
   ```
6. **Test it** — run the relevant integration tests under `tests/integration/` (they use `testcontainers` to spin up a real Postgres and apply migrations).
7. **Commit the model change, the types change, and the migration file in one commit.** They must never be committed separately — a repo where `models.py` and `migrations/versions/` disagree is broken.

## Naming convention

Pass a **snake_case**, imperative-ish, description to `NAME`:

| Good | Bad |
|---|---|
| `add_is_verified_to_user` | `"added verified"` |
| `create_widget_table` | `"widget"` |
| `rename_user_email_to_login` | `"rename"` |
| `drop_legacy_permissions_column` | `"cleanup"` |
| `add_gin_index_on_user_login` | `"index"` |

Keep it under ~50 chars. The slug ends up in the filename and in `git log`, so it should stand alone.

## What NOT to do

- ❌ **Do not** write a new migration file by hand. Always use `make generate NAME="..."`. Autogenerate is the starting point even if you'll have to edit it.
- ❌ **Do not** call `alembic revision --autogenerate` directly. Use the Makefile target so the invocation is consistent across environments.
- ❌ **Do not** edit an existing migration file in `migrations/versions/` (`01_...py`, `02_...py`, etc.). These are **immutable history**. A PreToolUse hook (`.claude/hooks/guard_paths.py`) blocks any edit to these files — if you see the block, you're doing something wrong. If you need to fix a bug in a migration that was already applied, write a **new** migration that corrects it; don't rewrite history.
- ❌ **Do not** edit `migrations/env.py` casually — it's the Alembic bootstrap that the hook also protects. If you genuinely need to change it (e.g., to register a new metadata target), do it outside Claude's edit flow.
- ❌ **Do not** apply a migration without generating + inspecting the file first. Autogenerate output is your audit trail — if you skip it, you lose traceability.
- ❌ **Do not** autogenerate a migration against a schema that's out of sync with `head`. Run `make upgrade` first to bring the DB current, otherwise the diff will include changes from earlier, already-shipped migrations.

## When autogenerate is not enough

Autogenerate is blind to:

- **Data migrations** — if a new NOT NULL column needs a value for existing rows, you must write an `op.execute("UPDATE ...")` before the `op.alter_column(..., nullable=False)`.
- **Enum mutations** — Postgres enums need `op.execute("ALTER TYPE <name> ADD VALUE '<val>'")`; autogenerate doesn't emit this.
- **Complex index types** — GIN, GiST, partial indexes, expression indexes may need hand-written `op.create_index`.
- **Check constraints with SQL expressions** — autogenerate detects the constraint name but may miss the expression text.

For these cases: generate the migration normally, then **edit the generated file** (still allowed before commit) to add the missing `op.execute(...)` or `op.create_index(...)` calls, and update the `downgrade()` to reverse them.

## Rollback discipline

Every `upgrade()` must have a real `downgrade()`. Never leave `pass` in `downgrade()` unless the operation is genuinely irreversible (and even then, prefer raising `NotImplementedError` to make the intent explicit).

## Checklist (run this before handing back to the user)

- [ ] Edited the model in `src/database/psql/models/<entity>.py`
- [ ] Updated `Create<Entity>Type` / `Update<Entity>Type` / `<Entity>Loads` in `src/database/psql/types/<entity>.py` if applicable
- [ ] Ran `make generate NAME="<snake_case_desc>"`
- [ ] Opened the generated file and verified `upgrade()` / `downgrade()` match intent
- [ ] Added any missing data migrations, enum ops, or custom index calls
- [ ] Ran `make upgrade` locally
- [ ] Ran the relevant integration tests
- [ ] Staged model + types + migration together for one commit
