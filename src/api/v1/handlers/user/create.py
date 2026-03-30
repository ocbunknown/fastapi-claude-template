from dataclasses import dataclass
from typing import Annotated

import uuid_utils.compat as uuid
from pydantic import Field

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.api.v1.constants import (
    MAX_LOGIN_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from src.database import DBGateway
from src.services.interfaces.hasher import Hasher


class CreateUserQuery(DTO):
    login: Annotated[
        str,
        Field(
            max_length=MAX_LOGIN_LENGTH,
            description=(f"Login maximum length `{MAX_LOGIN_LENGTH}`"),
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
class CreateUserHandler(Handler[CreateUserQuery, dtos.User]):
    database: DBGateway
    hasher: Hasher

    async def __call__(self, query: CreateUserQuery) -> dtos.User:
        async with self.database:
            user = await self.database.user.create(
                login=query.login,
                password=self.hasher.hash_password(query.password),
                role_uuid=query.role_uuid,
            )

            return dtos.User(**user.result().as_dict())
