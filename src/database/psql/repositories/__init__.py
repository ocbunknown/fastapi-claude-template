from typing import Literal

from src.application.common.exceptions import (
    AppException,
    ForbiddenError,
    NotFoundError,
)

type ExceptionType = Literal["update", "delete", "select", "create", "exists", "count"]

exception_map: dict[ExceptionType, Exception] = {
    "update": ForbiddenError("Cannot be updated"),
    "delete": ForbiddenError("Cannot be deleted"),
    "select": NotFoundError("Not found"),
    "create": ForbiddenError("Cannot be created"),
    "exists": NotFoundError("Not found"),
    "count": NotFoundError("Not found"),
}


class Result[T]:
    __slots__ = ("data", "exception_type")

    def __init__(self, exception_type: ExceptionType, data: T | None) -> None:
        self.data = data
        self.exception_type = exception_type

    def result_or_none(self) -> T | None:
        return self.data

    def result(self) -> T:
        if self.data is not None:
            return self.data

        raise exception_map[self.exception_type]

    def result_or_raise(self, exception_to_raise: AppException) -> T:
        if self.data is not None:
            return self.data

        raise exception_to_raise
