import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from pydantic import Field

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.api.v1.constants import (
    MAX_LOGIN_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from src.common.exceptions import (
    ConflictError,
)
from src.common.tools.cache import default_key_builder
from src.database import DBGateway
from src.services import InternalServiceGateway
from src.services.cache.redis import RedisCache


class RegisterQuery(DTO):
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
    fingerprint: str


@dataclass(slots=True)
class RegisterHandler(Handler[RegisterQuery, dtos.Status]):
    internal_gateway: InternalServiceGateway
    database: DBGateway
    redis: RedisCache

    async def __call__(self, query: RegisterQuery) -> dtos.Status:
        async with self.database.manager.session:
            user = (await self.database.user.exists(login=query.login)).result()

        if user:
            raise ConflictError("User already exists")

        code = secrets.token_hex(16)

        await self.redis.set(
            default_key_builder(code=code),
            query.model_dump_json(),
            expire=timedelta(minutes=10),
        )

        return dtos.Status(status=True)
