from fastapi import APIRouter, FastAPI

from .admin import setup_admin_router
from .internal import setup_internal_router
from .public import setup_public_router
from .user import setup_user_router


def setup_v1_routers(app: FastAPI) -> None:
    router = APIRouter(prefix="/v1")

    router.include_router(setup_public_router())
    router.include_router(setup_user_router())
    router.include_router(setup_admin_router())
    router.include_router(setup_internal_router())

    app.include_router(router)
