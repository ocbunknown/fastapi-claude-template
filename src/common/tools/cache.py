from typing import Any


def default_key_builder(
    *keys: str,
    data: dict[str, Any] | None = None,
    separator: str = ".",
    **kwargs: Any,
) -> str:
    parts = list(keys)
    if data:
        parts.extend(f"{k}{separator}{v}" for k, v in data.items())

    parts.extend(f"{k}{separator}{v}" for k, v in kwargs.items())
    return separator.join(parts)
