from collections.abc import Sequence
from typing import Any, Optional, Unpack

import uuid_utils.compat as uuid
from sqlalchemy import ColumnExpressionArgument, UnaryExpression

import src.database.models as models
from src.database.exceptions import InvalidParamsError
from src.database.repositories import Result
from src.database.repositories.base import BaseRepository
from src.database.tools import on_integrity, select_with_relationships
from src.database.types import OrderBy
from src.database.types.user import (
    CreateUserType,
    UpdateUserType,
    UserLoads,
)


class UserRepository(BaseRepository[models.User]):
    __slots__ = ()

    @on_integrity("login")
    async def create(self, **data: Unpack[CreateUserType]) -> Result[models.User]:
        return Result("create", await self._crud.insert(**data))

    async def select(
        self,
        *loads: UserLoads,
        user_uuid: Optional[uuid.UUID] = None,
        login: Optional[str] = None,
    ) -> Result[models.User]:
        if not any([user_uuid, login]):
            raise InvalidParamsError("at least one identifier must be provided")

        where_clauses: list[ColumnExpressionArgument[bool]] = []

        if user_uuid:
            where_clauses.append(self.model.uuid == user_uuid)
        if login:
            where_clauses.append(self.model.login == login)

        stmt = select_with_relationships(*loads, model=self.model).where(*where_clauses)
        return Result("select", (await self._session.scalars(stmt)).unique().first())

    @on_integrity("login")
    async def update(
        self,
        uuid: uuid.UUID,
        /,
        **data: Unpack[UpdateUserType],
    ) -> Result[models.User]:
        if not any([uuid]):
            raise InvalidParamsError("at least one identifier must be provided")

        result = await self._crud.update(self.model.uuid == uuid, **data)
        return Result("update", result[0] if result else None)

    async def delete(
        self, user_uuid: Optional[uuid.UUID] = None, login: Optional[str] = None
    ) -> Result[models.User]:
        if not any([user_uuid, login]):
            raise InvalidParamsError("at least one identifier must be provided")

        where_clauses: list[ColumnExpressionArgument[bool]] = []

        if user_uuid:
            where_clauses.append(self.model.uuid == user_uuid)
        if login:
            where_clauses.append(self.model.login == login)

        result = await self._crud.delete(*where_clauses)
        return Result("delete", result[0] if result else None)

    async def select_many(
        self,
        *loads: UserLoads,
        login: Optional[str] = None,
        role_uuid: Optional[uuid.UUID] = None,
        order_by: OrderBy = "desc",
        offset: int = 0,
        limit: int = 10,
    ) -> Result[tuple[int, Sequence[models.User]]]:
        where_clauses: list[ColumnExpressionArgument[bool]] = []
        order_by_clauses: list[UnaryExpression[Any]] = []

        if login:
            where_clauses.append(self.model.login.ilike(f"%{login}%"))
        if role_uuid:
            where_clauses.append(self.model.role_uuid == role_uuid)
        if order_by:
            order_by_clauses.append(getattr(self.model.created_at, order_by)())

        total = await self._crud.count(*where_clauses)
        if total <= 0:
            return Result("select", (total, []))

        stmt = (
            select_with_relationships(*loads, model=self.model)
            .where(*where_clauses)
            .order_by(*order_by_clauses)
            .limit(limit)
            .offset(offset)
        )

        results = (await self._session.scalars(stmt)).unique().all()
        return Result("select", (total, results))

    async def exists(self, login: str) -> Result[bool]:
        return Result("exists", await self._crud.exists(self.model.login == login))
