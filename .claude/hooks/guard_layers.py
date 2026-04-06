#!/usr/bin/env python3
"""PreToolUse guard for layer dependency rules (per CLAUDE.md).

Inspects the *new* content about to be written to a .py file and blocks it
if it contains imports that would violate the project's layer rules:

  application/   → forbidden: infrastructure/, presentation/, consumers/, tasks/
  database/      → forbidden: infrastructure/, presentation/, consumers/, tasks/
  infrastructure/→ forbidden: presentation/, consumers/, tasks/, database/
  presentation/  → forbidden: consumers/, tasks/
  consumers/     → forbidden: presentation/, tasks/
  tasks/         → forbidden: presentation/, consumers/
  common/        → forbidden: application/, database/, infrastructure/,
                              presentation/, consumers/, tasks/, entrypoints/
  settings/      → forbidden: everything above except stdlib/3rd-party

Note: application/ may import from database/ directly (documented exception
in CLAUDE.md — database/ is a first-class shared kernel for persistence).
entrypoints/ is the composition root and may import from anywhere.

Reads PreToolUse JSON from stdin. Exits 2 to block with explanation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LAYER_RULES: dict[str, tuple[str, ...]] = {
    "application": ("infrastructure", "presentation", "consumers", "tasks"),
    "database": ("infrastructure", "presentation", "consumers", "tasks"),
    "infrastructure": ("presentation", "consumers", "tasks", "database"),
    "presentation": ("consumers", "tasks"),
    "consumers": ("presentation", "tasks"),
    "tasks": ("presentation", "consumers"),
    "common": (
        "application",
        "database",
        "infrastructure",
        "presentation",
        "consumers",
        "tasks",
        "entrypoints",
    ),
    "settings": (
        "application",
        "database",
        "infrastructure",
        "presentation",
        "consumers",
        "tasks",
        "entrypoints",
        "common",
    ),
}

# application → database is the documented exception (CLAUDE.md "Persistence").
# entrypoints → anything is fine (composition root).
SKIP_PREFIXES = ("entrypoints",)

IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+(src\.[\w.]+)",
    re.MULTILINE,
)


def source_layer(rel_path: str) -> str | None:
    parts = rel_path.split("/")
    if len(parts) < 2 or parts[0] != "src":
        return None
    return parts[1]


def extract_new_content(tool_name: str, tool_input: dict[str, object]) -> str:
    """Return the text that will land in the file after the edit."""
    if tool_name == "Write":
        return str(tool_input.get("content") or "")
    if tool_name == "Edit":
        return str(tool_input.get("new_string") or "")
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        if not isinstance(edits, list):
            return ""
        return "\n".join(
            str(e.get("new_string") or "") for e in edits if isinstance(e, dict)
        )
    return ""


def find_violations(
    source_layer_name: str, content: str
) -> list[tuple[str, str]]:
    forbidden = LAYER_RULES.get(source_layer_name, ())
    if not forbidden:
        return []

    violations: list[tuple[str, str]] = []
    for match in IMPORT_RE.finditer(content):
        imported = match.group(1)
        parts = imported.split(".")
        if len(parts) < 2:
            continue
        target_layer = parts[1]
        if target_layer in forbidden:
            violations.append((imported, target_layer))
    return violations


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    file_path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path or not str(file_path).endswith(".py"):
        return 0

    cwd = payload.get("cwd") or ""
    try:
        rel = str(Path(str(file_path)).resolve().relative_to(Path(str(cwd)).resolve()))
    except (ValueError, OSError):
        return 0

    src_layer = source_layer(rel)
    if src_layer is None or src_layer in SKIP_PREFIXES:
        return 0

    content = extract_new_content(str(tool_name), tool_input)
    if not content:
        return 0

    violations = find_violations(src_layer, content)
    if not violations:
        return 0

    lines = [
        f"[guard_layers] layer violation in {rel} (layer: {src_layer})",
        "  forbidden imports:",
    ]
    for imp, target in violations:
        lines.append(f"    - {imp}  (→ forbidden layer: {target})")
    lines.append(
        "  see CLAUDE.md → 'Layer dependency rules'. "
        "Outer-layer code must go through application/common/interfaces/ ports."
    )
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
