from fastapi import APIRouter, status

from src.api.v1 import dtos

healthcheck_router = APIRouter(prefix="/healthcheck", tags=["Healthcheck"])


@healthcheck_router.get("/healthcheck", status_code=status.HTTP_200_OK)
async def healthcheck_endpoint() -> dtos.Status:
    return dtos.Status(status=True)
