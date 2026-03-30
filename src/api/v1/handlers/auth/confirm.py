from dataclasses import dataclass

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.common.exceptions import NotFoundError
from src.common.tools.cache import default_key_builder
from src.database import DBGateway
from src.services import InternalServiceGateway
from src.services.cache.redis import RedisCache
from src.services.interfaces.hasher import Hasher
from src.services.internal.auth import TokensExpire


class ConfirmRegisterQuery(DTO):
    code: str


@dataclass(slots=True)
class ConfirmRegisterHandler(Handler[ConfirmRegisterQuery, TokensExpire]):
    internal_gateway: InternalServiceGateway
    database: DBGateway
    hasher: Hasher
    redis: RedisCache

    async def __call__(self, query: ConfirmRegisterQuery) -> TokensExpire:
        key = default_key_builder(code=query.code)

        cached_data = await self.redis.get(key)
        if not cached_data:
            raise NotFoundError("Code has expire or invalid")

        await self.redis.delete(key)
        cache_user = dtos.Register.model_validate_json(cached_data)

        async with self.database:
            role = (await self.database.role.select(name="User")).result()
            user = (
                await self.database.user.create(
                    login=cache_user.login,
                    password=self.hasher.hash_password(cache_user.password),
                    role_uuid=role.uuid,
                )
            ).result()

        return await self.internal_gateway.auth.login(cache_user.fingerprint, user.uuid)
