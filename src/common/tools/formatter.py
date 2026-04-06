import string
from typing import Any


class SafeFormatter(string.Formatter):
    def get_value(self, key: Any, args: Any, kwargs: Any) -> Any:
        try:
            return super().get_value(key, args, kwargs)
        except KeyError:
            return f"{{{key}}}"


def extract_keys_formatter(text: str) -> list[str]:
    return [
        field[1] for field in string.Formatter().parse(text) if field[1] is not None
    ]
