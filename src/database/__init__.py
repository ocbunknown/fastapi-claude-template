from typing import Any, Callable

from src.database import models
from src.database.connection import SessionFactoryType
from src.database.interfaces.gateway import BaseGateway
from src.database.manager import TransactionManager
from src.database.queries.executor import QueryExecutor
from src.database.repositories.role import RoleRepository
from src.database.repositories.user import UserRepository


class DBGateway(BaseGateway):
    __slots__ = ("manager", "_cache")

    def __init__(self, manager: TransactionManager) -> None:
        super().__init__(manager)
        self.manager = manager
        self._cache: dict[str, Any] = {}

    @property
    def query_executor(self) -> QueryExecutor:
        return self._from_cache("query_executor", QueryExecutor)

    @property
    def user(self) -> UserRepository:
        return self._from_cache("user", UserRepository, model=models.User)

    @property
    def role(self) -> RoleRepository:
        return self._from_cache("role", RoleRepository, model=models.Role)

    def _from_cache[S](self, key: str, factory: Callable[..., S], **kwargs: Any) -> S:
        if not (cached := self._cache.get(key)):
            cached = factory(self.manager.session, **kwargs)
            self._cache[key] = cached

        return cached


def create_database_factory(
    manager: type[TransactionManager], session_factory: SessionFactoryType
) -> Callable[[], DBGateway]:
    def _create() -> DBGateway:
        return DBGateway(manager(session_factory()))

    return _create


__all__ = ("DBGateway", "create_database_factory")
