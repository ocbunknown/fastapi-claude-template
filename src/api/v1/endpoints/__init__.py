from fastapi import APIRouter, FastAPI

from .admin import setup_admin_router
from .auth import auth_router
from .healthcheck import healthcheck_router


def setup_v1_routers(app: FastAPI) -> None:
    router = APIRouter()

    router.include_router(healthcheck_router)
    router.include_router(auth_router)

    router.include_router(setup_admin_router())
    app.include_router(router)
