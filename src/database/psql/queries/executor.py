from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.psql.queries.base import QueryObject


class QueryExecutor:
    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __call__[R](self, query: QueryObject[Any, R]) -> R:
        return await query(self._session)
