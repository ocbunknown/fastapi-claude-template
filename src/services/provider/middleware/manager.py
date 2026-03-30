import typing as t
from functools import partial

from src.services.provider.middleware.base import (
    CallNextMiddlewareType,
    RequestMiddlewareType,
)


class RequestMiddlewareManager(t.Sequence[RequestMiddlewareType]):
    def __init__(self, *middlewares: RequestMiddlewareType) -> None:
        self._middlewares: t.List[RequestMiddlewareType] = list(middlewares)

    def register(
        self,
        middleware: RequestMiddlewareType,
    ) -> RequestMiddlewareType:
        self._middlewares.append(middleware)
        return middleware

    __call__ = register

    def unregister(self, middleware: RequestMiddlewareType) -> None:
        self._middlewares.remove(middleware)

    @t.overload
    def __getitem__(self, item: int) -> RequestMiddlewareType: ...
    @t.overload
    def __getitem__(self, item: slice) -> t.Sequence[RequestMiddlewareType]: ...
    def __getitem__(
        self, item: t.Union[int, slice]
    ) -> t.Union[RequestMiddlewareType, t.Sequence[RequestMiddlewareType]]:
        return self._middlewares[item]

    def __len__(self) -> int:
        return len(self._middlewares)

    def wrap_middleware(
        self, callback: CallNextMiddlewareType, **kw: t.Any
    ) -> CallNextMiddlewareType:
        middleware = partial(callback, **kw)

        for m in reversed(self._middlewares):
            middleware = partial(m, middleware)

        return middleware
