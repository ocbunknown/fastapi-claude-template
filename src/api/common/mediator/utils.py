import inspect
from typing import Any, Callable, Optional, cast

from src.api.common.interfaces.handler import HandlerType

type Dependency = Callable[[], Any] | Any


def _resolve_factory[T](handler: Callable[[], T] | T, compare_with: type[Any]) -> T:
    if isinstance(handler, compare_with):
        return cast(T, handler)

    return handler() if callable(handler) else handler


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


def _create_handler_factory[D: Dependency](
    handler: type[HandlerType], **dependencies: D
) -> Callable[[], HandlerType]:
    def _factory() -> HandlerType:
        return handler(
            **{k: v() if callable(v) else v for k, v in dependencies.items()}
        )

    return _factory


def _retrieve_handler_params(handler: type[HandlerType]) -> dict[str, Any]:
    return {k: v.annotation for k, v in inspect.signature(handler).parameters.items()}
