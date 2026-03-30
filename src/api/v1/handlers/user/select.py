from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.database import DBGateway
from src.database.types.user import UserLoads


class SelectUserQuery(DTO):
    loads: tuple[UserLoads, ...]
    user_uuid: uuid.UUID | None = None
    login: str | None = None


@dataclass(slots=True)
class SelectUserHandler(Handler[SelectUserQuery, dtos.User]):
    database: DBGateway

    async def __call__(self, query: SelectUserQuery) -> dtos.User:
        async with self.database.manager.session:
            user = await self.database.user.select(
                *query.loads,
                user_uuid=query.user_uuid,
                login=query.login,
            )

            return dtos.User(**user.result().as_dict())
