import abc
from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.base import Base


class QueryObject[S, R](abc.ABC):
    @abc.abstractmethod
    def build(self) -> S:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(self, session: AsyncSession, stmt: S) -> R:
        raise NotImplementedError

    async def __call__(self, session: AsyncSession) -> R:
        return await self.execute(session, self.build())


class ExtendableQueryObject[E: Base](
    QueryObject[sa.Select[tuple[E]], tuple[int, Sequence[E]]]
):
    @abc.abstractmethod
    def build(self) -> sa.Select[tuple[E]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def execute(
        self, session: AsyncSession, stmt: sa.Select[tuple[E]]
    ) -> tuple[int, Sequence[E]]:
        raise NotImplementedError

    async def __call__(self, session: AsyncSession) -> tuple[int, Sequence[E]]:
        return await self.execute(session, self.build())
