from dataclasses import dataclass

from src.application.common.exceptions import NotFoundError
from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.hasher import Hasher
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.services import ServiceGateway
from src.application.v1.services.auth import TokensExpire
from src.application.v1.usecases.auth.register import RegisterRequest
from src.common.tools.cache import default_cache_key_builder
from src.database.psql import DBGateway


class ConfirmRegisterRequest(Request):
    code: str


@dataclass(slots=True)
class ConfirmRegisterUseCase(UseCase[ConfirmRegisterRequest, TokensExpire]):
    services: ServiceGateway
    database: DBGateway
    hasher: Hasher
    cache: StrCache

    async def __call__(self, request: ConfirmRegisterRequest) -> TokensExpire:
        key = default_cache_key_builder(code=request.code)

        cached_data = await self.cache.get(key)
        if not cached_data:
            raise NotFoundError("Code has expire or invalid")

        await self.cache.delete(key)
        cached_user = RegisterRequest.model_validate_json(cached_data)

        async with self.database:
            role = (await self.database.role.select(name="User")).result()
            user = (
                await self.database.user.create(
                    login=cached_user.login,
                    password=self.hasher.hash_password(cached_user.password),
                    role_uuid=role.uuid,
                )
            ).result()

        return await self.services.auth.login(cached_user.fingerprint, user.uuid)
