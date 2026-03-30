import re
from typing import Any


def pascal_to_snake(obj: Any) -> str:
    snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", getattr(obj, "__name__", ""))
    return snake_case.lower()
