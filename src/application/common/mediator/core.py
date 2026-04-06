from typing import Any, Callable, Self

from src.application.common.interfaces.usecase import UseCase, UseCaseType
from src.application.common.mediator.utils import (
    _create_use_case_factory,
    _predict_dependency_or_raise,
    _resolve_factory,
    _retrieve_use_case_params,
)
from src.application.common.request import Request

type UseCaseLike = Callable[[], UseCaseType] | UseCaseType


class MediatorImpl:
    __slots__ = ("_use_cases_registry", "_use_cases_factory", "_dependencies")

    def __init__(self) -> None:
        self._use_cases_registry: dict[type[Request], UseCaseLike] = {}
        self._use_cases_factory: set[Callable[[Self], None]] = set()
        self._dependencies: dict[str, Any] = {}

    @classmethod
    def builder(cls) -> Self:
        return cls()

    def dependencies(self, **dependencies: Any) -> Self:
        self._dependencies = dependencies
        return self

    def use_cases(self, *use_cases_factory: Callable[[Self], None]) -> Self:
        self._use_cases_factory = set(use_cases_factory)
        return self

    def build(self) -> Self:
        for use_case_factory in self._use_cases_factory:
            use_case_factory(self)
        return self

    def register[Q: Request](
        self, request: type[Q], use_case: type[UseCaseType]
    ) -> None:
        prepared_deps = _predict_dependency_or_raise(
            provided=_retrieve_use_case_params(use_case),
            required=self._dependencies,
            non_checkable={"request"},
        )
        self._use_cases_registry[request] = _create_use_case_factory(
            use_case, **prepared_deps
        )

    async def send[Q: Request, R](self, request: Q) -> R:
        use_case: UseCase[Q, R] = self._get_use_case(request)
        return await use_case(request)

    def _get_use_case[Q: Request, R](self, request: Q) -> UseCase[Q, R]:
        try:
            return _resolve_factory(self._use_cases_registry[type(request)], UseCase)
        except KeyError as e:
            raise KeyError(f"Use case for `{type(request)}` is not registered") from e
