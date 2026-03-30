from dataclasses import dataclass

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.common.exceptions import (
    ForbiddenError,
    ServiceNotImplementedError,
    UnAuthorizedError,
)
from src.database import DBGateway
from src.database.models.types import Roles
from src.services import InternalServiceGateway
from src.services.interfaces.hasher import Hasher


class PermissionQuery(DTO):
    permissions: tuple[Roles | None, ...]
    access_token: str
    refresh_token: str


@dataclass(slots=True)
class PermissionHandler(Handler[PermissionQuery, dtos.PrivateUser]):
    database: DBGateway
    hasher: Hasher
    internal_gateway: InternalServiceGateway

    async def __call__(self, query: PermissionQuery) -> dtos.PrivateUser:
        user_uuid = await self.internal_gateway.auth.verify_token(
            query.access_token, "access"
        )

        async with self.database.manager.session:
            user = (
                await self.database.user.select("role", user_uuid=user_uuid)
            ).result()

        if not user.active:
            raise ForbiddenError("You have been blocked")
        if not user.role:
            raise ServiceNotImplementedError("Role not found")
        if allowed_roles := query.permissions:
            if user.role.name not in allowed_roles:
                raise UnAuthorizedError("Not Allowed")

        return dtos.PrivateUser(
            **user.as_dict(),
            access_token=query.access_token,
            refresh_token=query.refresh_token,
        )
