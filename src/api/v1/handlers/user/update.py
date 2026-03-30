from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.database import DBGateway
from src.services.interfaces.hasher import Hasher


class UpdateUserQuery(DTO):
    user_uuid: uuid.UUID
    password: str | None = None


@dataclass(slots=True)
class UpdateUserHandler(Handler[UpdateUserQuery, dtos.User]):
    database: DBGateway
    hasher: Hasher

    async def __call__(self, query: UpdateUserQuery) -> dtos.User:
        async with self.database:
            if query.password:
                query.password = self.hasher.hash_password(query.password)

            user = await self.database.user.update(
                query.user_uuid,
                **query.model_dump(exclude_none=True, exclude={"user_uuid"}),
            )

            return dtos.User(**user.result().as_dict())
