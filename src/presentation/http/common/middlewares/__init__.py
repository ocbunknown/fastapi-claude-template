from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.settings.core import ServerSettings

from .request_id import RequestIDMiddleware


def setup_global_middlewares(app: FastAPI, server: ServerSettings) -> None:
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=server.origins,
        allow_methods=server.methods,
        allow_headers=server.headers,
    )
