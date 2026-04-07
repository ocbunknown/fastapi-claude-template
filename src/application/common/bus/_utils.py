import inspect
from typing import Any, Callable, Optional, cast

from src.application.common.interfaces.usecase import UseCaseType

type Dependency = Callable[[], Any] | Any


def _resolve_factory[T](use_case: Callable[[], T] | T, compare_with: type[Any]) -> T:
    if isinstance(use_case, compare_with):
        return cast(T, use_case)

    return use_case() if callable(use_case) else use_case


def _predict_dependency_or_raise(
    provided: dict[str, Any],
    required: dict[str, Any],
    non_checkable: Optional[set[str]] = None,
) -> dict[str, Any]:
    non_checkable = non_checkable or set()
    missing = [k for k in provided if k not in required and k not in non_checkable]
    if missing:
        missing_details = ", ".join(f"`{k}`:`{provided[k]}`" for k in missing)
        raise TypeError(f"Did you forget to set dependency for {missing_details}?")

    return {k: required.get(k, provided[k]) for k in provided}


def _create_use_case_factory[D: Dependency](
    use_case: type[UseCaseType], **dependencies: D
) -> Callable[[], UseCaseType]:
    def _factory() -> UseCaseType:
        return use_case(
            **{k: v() if callable(v) else v for k, v in dependencies.items()}
        )

    return _factory


def _retrieve_use_case_params(use_case: type[UseCaseType]) -> dict[str, Any]:
    return {k: v.annotation for k, v in inspect.signature(use_case).parameters.items()}
