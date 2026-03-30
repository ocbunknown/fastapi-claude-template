from typing import Any, Callable

type _AnyDependency = Callable[[], Any]


def singleton[DependencyType](
    dependency: DependencyType,
) -> Callable[[], DependencyType]:
    def singleton_factory() -> DependencyType:
        return dependency

    return singleton_factory


def lazy[T](
    v: Callable[..., T], *args: _AnyDependency, **deps: _AnyDependency
) -> Callable[[], T]:
    def _factory() -> T:
        return v(*(arg() for arg in args), **{k: dep() for k, dep in deps.items()})

    return _factory


def lazy_single[T, D](v: Callable[[D], T], dep: Callable[[], D]) -> Callable[[], T]:
    return lazy(v, dep)
