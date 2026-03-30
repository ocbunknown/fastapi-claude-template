from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

from .exceptions import handle_exception_middleware
from .request_id import set_request_id_middleware


def setup_global_middlewares(app: FastAPI) -> None:
    app.add_middleware(BaseHTTPMiddleware, dispatch=set_request_id_middleware)
    app.add_middleware(ServerErrorMiddleware, handler=handle_exception_middleware)
