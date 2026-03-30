from typing import TYPE_CHECKING, TypeVar, Union, cast

from dishka import FromDishka

T = TypeVar("T")

if TYPE_CHECKING:
    Depends = Union[T, T]
else:

    class Depends(FromDishka): ...


def FromDepends[T]() -> Depends[T]:
    return cast(Depends[T], ...)
