from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.application.common.interfaces.usecase import UseCase
from src.application.common.pagination import OffsetPagination
from src.application.common.request import Request
from src.application.v1.results import OffsetResult, UserResult
from src.database.psql import DBGateway
from src.database.psql.types.user import UserLoads


class SelectManyUserRequest(Request):
    loads: tuple[UserLoads, ...] = ()
    login: str | None = None
    role_uuid: uuid.UUID | None = None
    pagination: OffsetPagination = OffsetPagination()


@dataclass(slots=True)
class SelectManyUserUseCase(UseCase[SelectManyUserRequest, OffsetResult[UserResult]]):
    database: DBGateway

    async def __call__(
        self, request: SelectManyUserRequest
    ) -> OffsetResult[UserResult]:
        async with self.database.manager.session:
            total, users = (
                await self.database.user.select_many(
                    *request.loads,
                    login=request.login,
                    role_uuid=request.role_uuid,
                    **request.pagination.model_dump(),
                )
            ).result()

            return OffsetResult[UserResult](
                data=[UserResult(**user.as_dict()) for user in users],
                offset=request.pagination.offset,
                limit=request.pagination.limit,
                total=total,
            )
