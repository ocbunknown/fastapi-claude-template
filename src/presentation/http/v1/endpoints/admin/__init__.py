from fastapi import APIRouter
from fastapi import Depends as Require

from src.presentation.http.v1.guards import Authorization

from .user import admin_user_router


def setup_admin_router() -> APIRouter:
    router = APIRouter(
        prefix="/admin",
        dependencies=[Require(Authorization("Admin"))],
    )
    router.include_router(admin_user_router)
    return router
