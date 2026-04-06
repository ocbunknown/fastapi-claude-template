#!/usr/bin/env python3
"""PreToolUse guard for `git commit`.

When Claude runs a Bash command containing `git commit`, this hook:
  1. Runs `.venv/bin/ruff check src/ tests/`
  2. Runs `.venv/bin/mypy src/ tests/`

If either fails, the commit is blocked (exit 2) and errors are printed so
Claude can fix them before retrying.

Skips if the command is not a real commit (e.g., `git commit --help`) or if
the venv tools are missing.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

RUFF = ".venv/bin/ruff"
MYPY = ".venv/bin/mypy"

COMMIT_RE = re.compile(r"(^|[\s;&|])git\s+(-[^\s]+\s+)*commit(\s|$)")
SKIP_FLAG_RE = re.compile(r"(--help|--dry-run)")


def run(cmd: list[str], cwd: str) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=False)
    out = proc.stdout.decode() + proc.stderr.decode()
    return proc.returncode, out


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    command = str(tool_input.get("command") or "")
    if not COMMIT_RE.search(command) or SKIP_FLAG_RE.search(command):
        return 0

    cwd = str(payload.get("cwd") or os.getcwd())
    ruff_bin = Path(cwd) / RUFF
    mypy_bin = Path(cwd) / MYPY
    if not ruff_bin.exists() or not mypy_bin.exists():
        return 0  # dev tools not installed — don't block

    # Ruff first (fast)
    rc, out = run([str(ruff_bin), "check", "src/", "tests/"], cwd)
    if rc != 0:
        sys.stderr.write(
            "[pre_commit_checks] ruff check failed — fix lint errors before committing:\n"
            f"{out}\n"
        )
        return 2

    # Mypy strict
    rc, out = run([str(mypy_bin), "src/", "tests/"], cwd)
    if rc != 0:
        sys.stderr.write(
            "[pre_commit_checks] mypy failed — fix type errors before committing:\n"
            f"{out}\n"
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
