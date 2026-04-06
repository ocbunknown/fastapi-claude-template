from dataclasses import dataclass
from typing import Annotated

import uuid_utils.compat as uuid
from pydantic import Field

from src.application.common.interfaces.hasher import Hasher
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.constants import (
    MAX_LOGIN_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from src.application.v1.results import UserResult
from src.database.psql import DBGateway


class CreateUserRequest(Request):
    login: Annotated[
        str,
        Field(
            max_length=MAX_LOGIN_LENGTH,
            description=f"Login maximum length `{MAX_LOGIN_LENGTH}`",
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=MIN_PASSWORD_LENGTH,
            max_length=MAX_PASSWORD_LENGTH,
            description=(
                f"Password between `{MIN_PASSWORD_LENGTH}` and "
                f"`{MAX_PASSWORD_LENGTH}` characters long"
            ),
        ),
    ]
    role_uuid: uuid.UUID


@dataclass(slots=True)
class CreateUserUseCase(UseCase[CreateUserRequest, UserResult]):
    database: DBGateway
    hasher: Hasher

    async def __call__(self, request: CreateUserRequest) -> UserResult:
        async with self.database:
            user = (
                await self.database.user.create(
                    login=request.login,
                    password=self.hasher.hash_password(request.password),
                    role_uuid=request.role_uuid,
                )
            ).result()
            return UserResult.model_validate(user)
