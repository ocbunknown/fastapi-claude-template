from fastapi import FastAPI

from .request_id import RequestIDMiddleware


def setup_global_middlewares(app: FastAPI) -> None:
    app.add_middleware(RequestIDMiddleware)
