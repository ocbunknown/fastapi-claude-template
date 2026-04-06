import abc
from collections.abc import Mapping, Sequence
from typing import Any, Optional


class AbstractCRUDRepository[EntryType](abc.ABC):
    __slots__ = ("model",)

    def __init__(self, model: type[EntryType]) -> None:
        self.model = model

    @abc.abstractmethod
    async def insert(self, **values: Mapping[str, Any]) -> Optional[EntryType]:
        raise NotImplementedError

    @abc.abstractmethod
    async def insert_many(
        self, values: Sequence[Mapping[str, Any]]
    ) -> Sequence[EntryType]:
        raise NotImplementedError

    @abc.abstractmethod
    async def select(self, *clauses: Any) -> Optional[EntryType]:
        raise NotImplementedError

    @abc.abstractmethod
    async def select_many(
        self, *clauses: Any, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> Sequence[EntryType]:
        raise NotImplementedError

    @abc.abstractmethod
    async def update(
        self, *clauses: Any, **values: Mapping[str, Any]
    ) -> Sequence[EntryType]:
        raise NotImplementedError

    @abc.abstractmethod
    async def update_many(self, values: Sequence[Mapping[str, Any]]) -> Any:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, *clauses: Any) -> Sequence[EntryType]:
        raise NotImplementedError

    async def exists(self, *clauses: Any) -> bool:
        raise NotImplementedError

    async def count(self, *clauses: Any) -> int:
        raise NotImplementedError
