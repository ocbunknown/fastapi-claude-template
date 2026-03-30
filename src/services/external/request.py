import abc
from typing import Any

from src.services.provider.base import AsyncProvider


class Request[ResultType]:
    async def __call__(self, provider: AsyncProvider, **kwargs: Any) -> ResultType:
        return await self.handle(provider, **kwargs)

    @abc.abstractmethod
    async def handle(self, provider: AsyncProvider, **kwargs: Any) -> ResultType:
        raise NotImplementedError
