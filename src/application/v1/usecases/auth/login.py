from dataclasses import dataclass
from typing import Annotated

from pydantic import Field

from src.application.common.exceptions import ForbiddenError, UnAuthorizedError
from src.application.common.interfaces.hasher import Hasher
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.constants import (
    MAX_LOGIN_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from src.application.v1.services import ServiceGateway
from src.application.v1.services.auth import TokensExpire
from src.database.psql import DBGateway


class LoginRequest(Request):
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
class LoginUseCase(UseCase[LoginRequest, TokensExpire]):
    services: ServiceGateway
    database: DBGateway
    hasher: Hasher

    async def __call__(self, request: LoginRequest) -> TokensExpire:
        async with self.database.manager.session:
            user = (await self.database.user.select(login=request.login)).result()

        if not user.active:
            raise ForbiddenError("You have been blocked")
        if not self.hasher.verify_password(user.password, request.password):
            raise UnAuthorizedError("Incorrect password or login")

        return await self.services.auth.login(request.fingerprint, user.uuid)
