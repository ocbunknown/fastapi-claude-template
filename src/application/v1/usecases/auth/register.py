import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from pydantic import Field

from src.application.common.exceptions import ConflictError
from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.constants import (
    MAX_LOGIN_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from src.application.v1.results import StatusResult
from src.common.tools.cache import default_cache_key_builder
from src.database.psql import DBGateway


class RegisterRequest(Request):
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
    fingerprint: str


@dataclass(slots=True)
class RegisterUseCase(UseCase[RegisterRequest, StatusResult]):
    database: DBGateway
    cache: StrCache

    async def __call__(self, request: RegisterRequest) -> StatusResult:
        async with self.database.manager.session:
            user = (await self.database.user.exists(login=request.login)).result()

        if user:
            raise ConflictError("User already exists")

        code = secrets.token_hex(16)

        await self.cache.set(
            default_cache_key_builder(code=code),
            request.model_dump_json(),
            expire=timedelta(minutes=10),
        )

        return StatusResult(status=True)
