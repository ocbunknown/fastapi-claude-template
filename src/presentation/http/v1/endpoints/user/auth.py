from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Request, status
from fastapi import Depends as Require

from src.application.common.interfaces.request_bus import RequestBus
from src.application.v1.results import StatusResult, UserResult
from src.application.v1.usecases.auth import LogoutRequest
from src.common.di import Depends
from src.presentation.http.common.responses import OkResponse
from src.presentation.http.v1 import contracts
from src.presentation.http.v1.guards import Authorization

user_auth_router = APIRouter(prefix="/auth", tags=["User"], route_class=DishkaRoute)


@user_auth_router.post(
    "/logout",
    response_model=contracts.Status,
    status_code=status.HTTP_200_OK,
)
async def logout_endpoint(
    request_bus: Depends[RequestBus],
    request: Request,
    user: Annotated[UserResult, Require(Authorization())],
) -> OkResponse[contracts.Status]:
    result: StatusResult = await request_bus.send(
        LogoutRequest(
            user_uuid=user.uuid,
            refresh_token=request.cookies.get("refresh_token", ""),
        )
    )
    response = OkResponse(contracts.Status(status=result.status))
    response.delete_cookie("refresh_token")
    return response
