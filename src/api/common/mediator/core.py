from typing import Any, Callable, Self

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler, HandlerType
from src.api.common.mediator.utils import (
    _create_handler_factory,
    _predict_dependency_or_raise,
    _resolve_factory,
    _retrieve_handler_params,
)

type HandlerLike = Callable[[], HandlerType] | HandlerType


class MediatorImpl:
    __slots__ = ("_handlers_registry", "_handlers_factory", "_dependencies")

    def __init__(self) -> None:
        self._handlers_registry: dict[type[DTO], HandlerLike] = {}
        self._handlers_factory: set[Callable[[Self], None]] = set()
        self._dependencies: dict[str, Any] = {}

    @classmethod
    def builder(cls) -> Self:
        return cls()

    def dependencies(self, **dependencies: Any) -> Self:
        self._dependencies = dependencies
        return self

    def handlers(self, *handlers_factory: Callable[[Self], None]) -> Self:
        self._handlers_factory = set(handlers_factory)
        return self

    def build(self) -> Self:
        for handler_factory in self._handlers_factory:
            handler_factory(self)
        return self

    def middleware(self) -> Self:
        return self

    def register[Q: DTO](self, query: type[Q], handler: type[HandlerType]) -> None:
        prepared_deps = _predict_dependency_or_raise(
            provided=_retrieve_handler_params(handler),
            required=self._dependencies,
            non_checkable={
                "query",
            },
        )
        self._handlers_registry[query] = _create_handler_factory(
            handler, **prepared_deps
        )

    async def send[Q: DTO, R: DTO](self, query: Q) -> R:
        handler: Handler[Q, R] = self._get_handler(query)
        return await handler(query)

    def _get_handler[Q: DTO, R: DTO](self, query: Q) -> Handler[Q, R]:
        try:
            return _resolve_factory(self._handlers_registry[type(query)], Handler)
        except KeyError as e:
            raise KeyError(f"Handler for `{type(query)}` is not registered") from e
