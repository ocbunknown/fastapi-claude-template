#!/usr/bin/env python3
"""PreToolUse guard for protected paths.

Blocks edits to files that should never be modified manually by Claude:
- Committed alembic migrations in migrations/versions/ (only create new ones
  via `make generate NAME=...` — never edit existing migration files)
- migrations/env.py (alembic bootstrap — hand-tuned)
- Lockfiles (uv.lock, poetry.lock) — only regenerate via tooling
- .env* secrets (but .env.example / .env.sample / .env.template are committed
  placeholders — explicitly allowed)
- pyproject.toml writes (dependency changes should be deliberate, via `uv add`)

Reads hook JSON from stdin. Exits 2 to block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Repo-relative regex patterns that are forbidden to edit.
FORBIDDEN = [
    r"^migrations/versions/\d+_[0-9a-f]+_.*\.py$",
    r"^migrations/env\.py$",
    r"^uv\.lock$",
    r"^poetry\.lock$",
    r"^\.env(\..*)?$",
    r"^pyproject\.toml$",
]

# Explicit allowlist — matched against the repo-relative path BEFORE the
# FORBIDDEN list. Use this for committed template files that live at a
# forbidden path but carry no secrets.
ALLOWLIST = [
    r"^\.env\.(example|sample|template)$",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # don't block on malformed input

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path:
        return 0

    cwd = payload.get("cwd") or ""
    try:
        rel = str(Path(file_path).resolve().relative_to(Path(cwd).resolve()))
    except (ValueError, OSError):
        rel = file_path

    for pattern in ALLOWLIST:
        if re.search(pattern, rel):
            return 0

    for pattern in FORBIDDEN:
        if re.search(pattern, rel):
            sys.stderr.write(
                f"[guard_paths] blocked edit to {rel}\n"
                f"  matched pattern: {pattern}\n"
                f'  hint: migrations → `make generate NAME="<desc>"`; '
                f"deps → `uv add <pkg>`; secrets → edit by hand outside Claude.\n"
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
