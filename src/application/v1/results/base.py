from collections.abc import Callable

from pydantic import BaseModel, ConfigDict


class Result(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)


class StatusResult(Result):
    status: bool


class OffsetResult[T](Result):
    data: list[T]
    offset: int = 0
    limit: int | None = None
    total: int

    def map[R](self, fn: Callable[[T], R]) -> "OffsetResult[R]":
        return OffsetResult[R](
            data=[fn(item) for item in self.data],
            offset=self.offset,
            limit=self.limit,
            total=self.total,
        )
