from fastapi import APIRouter, status

from src.presentation.http.v1 import contracts

healthcheck_router = APIRouter(prefix="/healthcheck", tags=["Public"])


@healthcheck_router.get("", status_code=status.HTTP_200_OK)
async def healthcheck_endpoint() -> contracts.Status:
    return contracts.Status(status=True)
