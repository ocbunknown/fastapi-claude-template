from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Bus[M](Protocol):
    async def send(self, message: M) -> Any: ...
