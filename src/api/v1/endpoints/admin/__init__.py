from fastapi import APIRouter


def setup_admin_router() -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    return router
