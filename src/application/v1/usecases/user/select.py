from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.results import UserResult
from src.database.psql import DBGateway
from src.database.psql.types.user import UserLoads


class SelectUserRequest(Request):
    loads: tuple[UserLoads, ...] = ()
    user_uuid: uuid.UUID | None = None
    login: str | None = None


@dataclass(slots=True)
class SelectUserUseCase(UseCase[SelectUserRequest, UserResult]):
    database: DBGateway

    async def __call__(self, request: SelectUserRequest) -> UserResult:
        async with self.database.manager.session:
            user = (
                await self.database.user.select(
                    *request.loads,
                    user_uuid=request.user_uuid,
                    login=request.login,
                )
            ).result()
            return UserResult(**user.as_dict())
