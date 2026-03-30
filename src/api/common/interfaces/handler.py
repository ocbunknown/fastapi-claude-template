import abc
from dataclasses import dataclass, is_dataclass
from typing import Any


class Handler[Q, R](abc.ABC):
    __slots__ = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if not is_dataclass(cls):
            dataclass(slots=kwargs.pop("slots", True), **kwargs)(cls)

    @abc.abstractmethod
    async def __call__(self, query: Q) -> R: ...


type HandlerType = Handler[Any, Any]
