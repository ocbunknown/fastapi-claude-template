from collections.abc import Sequence
from typing import Optional, Unpack

import uuid_utils.compat as uuid
from sqlalchemy import ColumnExpressionArgument

import src.database.psql.models as models
from src.database.psql.exceptions import InvalidParamsError
from src.database.psql.models.types import Roles
from src.database.psql.repositories import Result
from src.database.psql.repositories.base import BaseRepository
from src.database.psql.tools import (
    on_integrity,
    sqla_offset_query,
    sqla_select,
    unique_scalars,
)
from src.database.psql.types import OrderBy
from src.database.psql.types.role import (
    CreateRoleType,
    RoleLoads,
)


class RoleRepository(BaseRepository[models.Role]):
    __slots__ = ()

    @on_integrity("name")
    async def create(self, **data: Unpack[CreateRoleType]) -> Result[models.Role]:
        return Result("create", await self._crud.insert(**data))

    async def select(
        self,
        *loads: RoleLoads,
        role_uuid: Optional[uuid.UUID] = None,
        name: Optional[Roles] = None,
    ) -> Result[models.Role]:
        if not any([role_uuid, name]):
            raise InvalidParamsError("at least one identifier must be provided")

        where_clauses: list[ColumnExpressionArgument[bool]] = []

        if role_uuid:
            where_clauses.append(self.model.uuid == role_uuid)
        if name:
            where_clauses.append(self.model.name == name)

        stmt = sqla_select(model=self.model, loads=loads).where(*where_clauses)
        return Result(
            "select", unique_scalars(await self._session.execute(stmt)).first()
        )

    async def select_many(
        self,
        *loads: RoleLoads,
        name: Optional[str] = None,
        order_by: OrderBy = "desc",
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> Result[tuple[int, Sequence[models.Role]]]:
        where_clauses: list[ColumnExpressionArgument[bool]] = []

        if name:
            where_clauses.append(self.model.name.ilike(f"%{name}%"))

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

    async def exists(self, name: str) -> Result[bool]:
        return Result("exists", await self._crud.exists(self.model.name == name))
