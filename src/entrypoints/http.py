from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Optional

import structlog
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI

from src.entrypoints.container import build_container
from src.entrypoints.server import run_api_granian
from src.infrastructure.logging import setup_logging
from src.presentation.http.common.exception_handlers import setup_exception_handlers
from src.presentation.http.common.middlewares import setup_global_middlewares
from src.presentation.http.common.responses import ORJSONResponse
from src.presentation.http.v1.endpoints import setup_v1_routers
from src.settings.core import Settings, load_settings

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await app.state.dishka_container.close()


def create_app(
    settings: Settings,
    title: str = "FastAPI",
    version: str = "0.1.0",
    docs_url: Optional[str] = "/docs",
    redoc_url: Optional[str] = "/redoc",
    swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
    root_path: str = "",
    **kw: Any,
) -> FastAPI:
    log.info("Initialize HTTP application")

    app = FastAPI(
        title=title,
        version=version,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
        root_path=root_path,
        **kw,
    )

    container = build_container(settings, FastapiProvider())
    setup_dishka(container, app)

    setup_v1_routers(app)
    setup_exception_handlers(app)
    setup_global_middlewares(app)

    return app


def run(settings: Settings) -> None:
    match settings.server.type:
        case "granian":
            run_api_granian("src.entrypoints.http:app", settings.server)
        case _:
            raise ValueError(
                f"Unsupported server type: '{settings.server.type}'. "
                "Currently only 'granian' server type is supported."
            )


settings = load_settings()
setup_logging(settings)
app = create_app(settings)


if __name__ == "__main__":
    run(settings)
