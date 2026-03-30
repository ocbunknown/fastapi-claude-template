import inspect
from typing import Any, Awaitable, Callable, overload

from dishka import AsyncContainer, Container
from dishka.integrations.base import wrap_injection

from src.common.di.container import container


@overload
def inject[T, **P](func: Callable[P, T]) -> Callable[P, T]: ...


@overload
def inject[T, **P](func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]: ...


def inject[T, **P](func: Callable[P, T]) -> Callable[P, T] | Callable[P, Awaitable[T]]:
    if inspect.iscoroutinefunction(func):

        def container_getter(*args: Any, **kwargs: Any) -> AsyncContainer:
            return container.get_container()

        return wrap_injection(
            func=func,
            container_getter=container_getter,
            is_async=True,
            manage_scope=True,
        )

    def sync_container_getter(*args: Any, **kwargs: Any) -> Container:
        return container.get_sync_container()

    return wrap_injection(
        func=func,
        container_getter=sync_container_getter,
        is_async=False,
        manage_scope=True,
    )
