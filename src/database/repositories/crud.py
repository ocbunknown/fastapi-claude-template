from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import (
    Any,
    Optional,
    cast,
)

from sqlalchemy import (
    ColumnExpressionArgument,
    CursorResult,
    UnaryExpression,
    delete,
    exists,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.interfaces.crud import AbstractCRUDRepository
from src.database.models.base import Base


class CRUDRepository[M: Base](AbstractCRUDRepository[M]):
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession, model: type[M]) -> None:
        super().__init__(model)
        self._session = session

    async def insert(self, **values: Any) -> Optional[M]:
        stmt = insert(self.model).values(**values).returning(self.model)
        return (await self._session.execute(stmt)).scalars().first()

    async def insert_many(self, data: Sequence[Mapping[str, Any]]) -> Sequence[M]:
        stmt = insert(self.model).returning(self.model)
        result = await self._session.scalars(stmt, data)
        return result.all()

    async def select(
        self,
        *clauses: ColumnExpressionArgument[bool],
    ) -> Optional[M]:
        stmt = select(self.model).where(*clauses)
        return (await self._session.execute(stmt)).scalars().first()

    async def select_many(
        self,
        *clauses: ColumnExpressionArgument[bool],
        order_by: Optional[list[UnaryExpression[Any]]] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Sequence[M]:
        stmt = select(self.model).where(*clauses).offset(offset).limit(limit)
        if order_by:
            stmt = stmt.order_by(*order_by)

        return (await self._session.execute(stmt)).scalars().all()

    async def update(
        self, *clauses: ColumnExpressionArgument[bool], **values: Any
    ) -> Sequence[M]:
        stmt = update(self.model).where(*clauses).values(**values).returning(self.model)
        return (await self._session.execute(stmt)).scalars().all()

    async def update_many(self, data: Sequence[Mapping[str, Any]]) -> CursorResult[Any]:
        return await self._session.execute(update(self.model), data)

    async def delete(self, *clauses: ColumnExpressionArgument[bool]) -> Sequence[M]:
        stmt = delete(self.model).where(*clauses).returning(self.model)
        return (await self._session.execute(stmt)).scalars().all()

    async def exists(self, *clauses: ColumnExpressionArgument[bool]) -> bool:
        stmt = exists(select(self.model).where(*clauses)).select()
        return cast(bool, await self._session.scalar(stmt))

    async def count(self, *clauses: ColumnExpressionArgument[bool]) -> int:
        stmt = select(func.count()).where(*clauses).select_from(self.model)
        return cast(int, await self._session.scalar(stmt))

    async def upsert(self, *conflict_columns: str, **values: Any) -> Optional[M]:
        stmt = (
            postgres_insert(self.model)
            .values(**values)
            .on_conflict_do_update(
                index_elements=conflict_columns,
                set_={
                    key: values[key] for key in values if key not in conflict_columns
                },
            )
            .returning(self.model)
        )
        return (await self._session.execute(stmt)).scalars().first()

    async def upsert_many(
        self, *conflict_columns: str, data: Sequence[Mapping[str, Any]]
    ) -> Sequence[M]:
        stmt = postgres_insert(self.model).values(data)
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={
                key: getattr(stmt.excluded, key)
                for key in data[0]
                if key not in conflict_columns
            },
        ).returning(self.model)  # type: ignore

        return (await self._session.execute(stmt)).scalars().all()

    def with_query_model(self, model: type[M]) -> CRUDRepository[M]:
        return CRUDRepository(self._session, model)
