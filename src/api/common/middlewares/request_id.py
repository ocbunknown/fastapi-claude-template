import uuid
from collections.abc import Awaitable
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response


async def set_request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request.state.request_id = uuid.uuid4().hex
    return await call_next(request)
