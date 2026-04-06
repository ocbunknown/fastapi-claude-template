from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.application.common.interfaces.hasher import Hasher
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.results import UserResult
from src.database.psql import DBGateway


class UpdateUserRequest(Request):
    user_uuid: uuid.UUID
    password: str | None = None
    role_uuid: uuid.UUID | None = None
    active: bool | None = None


@dataclass(slots=True)
class UpdateUserUseCase(UseCase[UpdateUserRequest, UserResult]):
    database: DBGateway
    hasher: Hasher

    async def __call__(self, request: UpdateUserRequest) -> UserResult:
        async with self.database:
            fields = request.model_dump(exclude_unset=True, exclude={"user_uuid"})
            if "password" in fields and fields["password"] is not None:
                fields["password"] = self.hasher.hash_password(fields["password"])

            user = (
                await self.database.user.update(request.user_uuid, **fields)
            ).result()
            return UserResult(**user.as_dict())
