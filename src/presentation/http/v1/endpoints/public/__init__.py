from fastapi import APIRouter

from .auth import public_auth_router
from .healthcheck import healthcheck_router


def setup_public_router() -> APIRouter:
    router = APIRouter()
    router.include_router(healthcheck_router)
    router.include_router(public_auth_router)
    return router
