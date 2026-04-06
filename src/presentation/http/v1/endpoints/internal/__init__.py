from fastapi import APIRouter


def setup_internal_router() -> APIRouter:
    return APIRouter(
        prefix="/internal",
        include_in_schema=False,
    )
