from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from src.api.common.exceptions import setup_exception_handlers
from src.api.common.middlewares import setup_global_middlewares
from src.api.common.responses import ORJSONResponse
from src.api.v1.di import setup_dependencies
from src.api.v1.endpoints import setup_v1_routers
from src.common.logger import log
from src.services.cache.redis import RedisCache
from src.services.provider.aiohttp import AiohttpProvider
from src.settings.core import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield

    finally:
        if engine := await app.state.dishka_container.get(AsyncEngine):
            await engine.dispose()
        if redis := await app.state.dishka_container.get(RedisCache):
            await redis.close()
        if aiohttp_provider := await app.state.dishka_container.get(AiohttpProvider):
            await aiohttp_provider.close_session()
        if ioc_container := app.state.dishka_container:
            await ioc_container.close()


def init_app_v1(
    settings: Settings,
    title: str = "FastAPI",
    version: str = "0.1.0",
    docs_url: Optional[str] = "/docs",
    redoc_url: Optional[str] = "/redoc",
    swagger_ui_oauth2_redirect_url: Optional[str] = "/docs/oauth2-redirect",
    **kw: Any,
) -> FastAPI:
    log.info("Initialize V1 API")
    app = FastAPI(
        title=title,
        version=version,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        swagger_ui_oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
        root_path="/api/v1",
        **kw,
    )
    setup_dependencies(app, settings)
    setup_v1_routers(app)
    setup_exception_handlers(app)
    setup_global_middlewares(app)

    return app
