from __future__ import annotations

from collections.abc import Awaitable
from functools import wraps
from typing import (
    Callable,
    Type,
    Union,
)

from sqla_autoloads import (
    add_conditions,
    sqla_cursor_query,
    sqla_offset_query,
    sqla_select,
    unique_scalars,
)
from sqlalchemy.exc import IntegrityError

from src.application.common.exceptions import AppException, ConflictError

__all__ = (
    "add_conditions",
    "on_integrity",
    "sqla_cursor_query",
    "sqla_offset_query",
    "sqla_select",
    "unique_scalars",
)


def on_integrity[R, **P](
    *uniques: str,
    should_raise: Union[Type[AppException], AppException] = ConflictError,
    base_message: str = "already in use",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def _wrapper(coro: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(coro)
        async def _inner_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await coro(*args, **kwargs)
            except IntegrityError as e:
                origin = str(e.orig)
                for uniq in uniques:
                    if uniq in origin:
                        if callable(should_raise):
                            message = f"{uniq} {base_message}"
                            raise should_raise(message) from e
                        else:
                            raise should_raise from e
                raise AppException() from e

        return _inner_wrapper

    return _wrapper
