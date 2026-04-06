from typing import Any


def default_cache_key_builder(
    data: dict[str, Any] | None = None, **kwargs: Any
) -> str:
    data = data or kwargs
    sorted_data = {key: data[key] for key in sorted(data.keys())}
    return ":".join(f"{k}:{v}" for k, v in sorted_data.items())
