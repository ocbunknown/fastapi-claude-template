from typing import Protocol, runtime_checkable

from src.application.common.interfaces.bus import Bus
from src.application.common.interfaces.wrapper import RequestWrapper
from src.application.common.request import Request


@runtime_checkable
class RequestBus(Bus[Request], Protocol):
    async def send[Q: Request, R](self, message: Q) -> R: ...
    async def send_wrapped[Q: Request, R](
        self, wrapper: RequestWrapper[Q, R], message: Q
    ) -> R: ...
