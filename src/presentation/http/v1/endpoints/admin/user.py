from typing import Annotated

import uuid_utils.compat as uuid
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Query, status
from fastapi import Depends as Require

from src.application.common.interfaces.request_bus import RequestBus
from src.application.common.pagination import OffsetPagination
from src.application.v1.results import OffsetResult, UserResult
from src.application.v1.usecases.user import (
    SelectManyUserRequest,
    SelectUserRequest,
    UpdateUserRequest,
)
from src.common.di import Depends
from src.database.psql.types.user import UserLoads
from src.presentation.http.common.responses import OkResponse
from src.presentation.http.v1 import contracts

admin_user_router = APIRouter(
    prefix="/users", tags=["Admin | User"], route_class=DishkaRoute
)


@admin_user_router.get(
    "",
    response_model=OffsetResult[contracts.User],
    status_code=status.HTTP_200_OK,
)
async def select_users_endpoint(
    request_bus: Depends[RequestBus],
    query: Annotated[contracts.SelectUsers, Require(contracts.SelectUsers)],
    pagination: Annotated[
        contracts.OffsetPagination, Require(contracts.OffsetPagination)
    ],
    loads: tuple[UserLoads, ...] = Query(default=(), title="Additional relations"),
) -> OkResponse[OffsetResult[contracts.User]]:
    result: OffsetResult[UserResult] = await request_bus.send(
        SelectManyUserRequest(
            loads=loads,
            **query.model_dump(),
            pagination=OffsetPagination(**pagination.model_dump()),
        )
    )
    return OkResponse(result.map(contracts.User.model_validate))


@admin_user_router.get(
    "/{user_uuid}",
    response_model=contracts.User,
    status_code=status.HTTP_200_OK,
)
async def select_user_endpoint(
    user_uuid: uuid.UUID,
    request_bus: Depends[RequestBus],
    loads: tuple[UserLoads, ...] = Query(default=(), title="Additional relations"),
) -> OkResponse[contracts.User]:
    result: UserResult = await request_bus.send(
        SelectUserRequest(user_uuid=user_uuid, loads=loads)
    )
    return OkResponse(contracts.User.model_validate(result))


@admin_user_router.patch(
    "/{user_uuid}",
    response_model=contracts.User,
    status_code=status.HTTP_200_OK,
)
async def update_user_endpoint(
    user_uuid: uuid.UUID,
    body: contracts.AdminUpdateUser,
    request_bus: Depends[RequestBus],
) -> OkResponse[contracts.User]:
    result: UserResult = await request_bus.send(
        UpdateUserRequest(
            user_uuid=user_uuid,
            **body.model_dump(exclude_unset=True),
        )
    )
    return OkResponse(contracts.User.model_validate(result))
