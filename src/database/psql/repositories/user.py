from collections.abc import Sequence
from typing import Optional, Unpack

import uuid_utils.compat as uuid
from sqlalchemy import ColumnExpressionArgument

import src.database.psql.models as models
from src.database.psql.exceptions import InvalidParamsError
from src.database.psql.repositories import Result
from src.database.psql.repositories.base import BaseRepository
from src.database.psql.tools import (
    on_integrity,
    sqla_offset_query,
    sqla_select,
    unique_scalars,
)
from src.database.psql.types import OrderBy
from src.database.psql.types.user import (
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

        stmt = sqla_select(model=self.model, loads=loads).where(*where_clauses)
        return Result(
            "select", unique_scalars(await self._session.execute(stmt)).first()
        )

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
        limit: Optional[int] = None,
    ) -> Result[tuple[int, Sequence[models.User]]]:
        where_clauses: list[ColumnExpressionArgument[bool]] = []

        if login:
            where_clauses.append(self.model.login.ilike(f"%{login}%"))
        if role_uuid:
            where_clauses.append(self.model.role_uuid == role_uuid)

        total = await self._crud.count(*where_clauses)
        if total <= 0:
            return Result("select", (total, []))

        stmt = sqla_offset_query(
            self.model,
            loads=loads,
            offset=offset,
            limit=limit,
            order=("created_at", order_by),
            where=where_clauses,
        )

        results = unique_scalars(await self._session.execute(stmt)).all()
        return Result("select", (total, results))

    async def exists(self, login: str) -> Result[bool]:
        return Result("exists", await self._crud.exists(self.model.login == login))
