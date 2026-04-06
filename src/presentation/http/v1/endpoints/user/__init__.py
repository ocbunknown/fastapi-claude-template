from fastapi import APIRouter
from fastapi import Depends as Require

from src.presentation.http.v1.guards import Authorization

from .auth import user_auth_router
from .me import user_me_router


def setup_user_router() -> APIRouter:
    router = APIRouter(dependencies=[Require(Authorization())])
    router.include_router(user_me_router)
    router.include_router(user_auth_router)
    return router
