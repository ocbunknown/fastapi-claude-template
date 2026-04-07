from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status
from fastapi import Depends as Require

from src.application.common.interfaces.request_bus import RequestBus
from src.application.v1.results import UserResult
from src.application.v1.usecases.user import (
    SelectUserRequest,
    UpdateUserRequest,
)
from src.common.di import Depends
from src.presentation.http.common.responses import OkResponse
from src.presentation.http.v1 import contracts
from src.presentation.http.v1.guards import Authorization

user_me_router = APIRouter(prefix="/users/me", tags=["User"], route_class=DishkaRoute)


@user_me_router.get(
    "",
    response_model=contracts.User,
    status_code=status.HTTP_200_OK,
)
async def get_me_endpoint(
    request_bus: Depends[RequestBus],
    user: Annotated[UserResult, Require(Authorization())],
) -> OkResponse[contracts.User]:
    result: UserResult = await request_bus.send(
        SelectUserRequest(user_uuid=user.uuid, loads=("role",))
    )
    return OkResponse(contracts.User.model_validate(result))


@user_me_router.patch(
    "",
    response_model=contracts.User,
    status_code=status.HTTP_200_OK,
)
async def update_self_endpoint(
    body: contracts.UpdateSelf,
    request_bus: Depends[RequestBus],
    user: Annotated[UserResult, Require(Authorization())],
) -> OkResponse[contracts.User]:
    result: UserResult = await request_bus.send(
        UpdateUserRequest(
            user_uuid=user.uuid,
            **body.model_dump(exclude_unset=True),
        )
    )
    return OkResponse(contracts.User.model_validate(result))
