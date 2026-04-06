#!/usr/bin/env python3
"""PostToolUse autoformat: run ruff format + ruff check --fix on the edited .py file.

Silent on success. Prints stderr on failure but does not block (exit 0/1 only).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RUFF = ".venv/bin/ruff"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path or not str(file_path).endswith(".py"):
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    ruff_bin = Path(cwd) / RUFF
    if not ruff_bin.exists():
        return 0  # no venv ruff, silent no-op

    abs_path = str(Path(str(file_path)).resolve())

    # format (idempotent)
    subprocess.run(
        [str(ruff_bin), "format", abs_path],
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    # autofix lints
    fix = subprocess.run(
        [str(ruff_bin), "check", "--fix", abs_path],
        cwd=cwd,
        capture_output=True,
        check=False,
    )
    if fix.returncode != 0 and fix.stderr:
        # non-blocking: surface remaining lint errors to Claude as advisory
        sys.stderr.write(
            f"[ruff_fix] remaining issues in {file_path}:\n{fix.stdout.decode()}\n"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
