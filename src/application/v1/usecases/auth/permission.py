from dataclasses import dataclass

from src.application.common.exceptions import (
    ForbiddenError,
    ServiceNotImplementedError,
    UnAuthorizedError,
)
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.results import UserResult
from src.application.v1.services import ServiceGateway
from src.database.psql import DBGateway
from src.database.psql.models.types import Roles


class PermissionRequest(Request):
    permissions: tuple[Roles | None, ...]
    access_token: str


@dataclass(slots=True)
class PermissionUseCase(UseCase[PermissionRequest, UserResult]):
    services: ServiceGateway
    database: DBGateway

    async def __call__(self, request: PermissionRequest) -> UserResult:
        user_uuid = await self.services.auth.verify_token(
            request.access_token, "access"
        )

        async with self.database.manager.session:
            user = (
                await self.database.user.select("role", user_uuid=user_uuid)
            ).result()

            if not user.active:
                raise ForbiddenError("You have been blocked")
            if not user.role:
                raise ServiceNotImplementedError("Role not found")
            if allowed_roles := request.permissions:
                if user.role.name not in allowed_roles:
                    raise UnAuthorizedError("Not Allowed")

            return UserResult(**user.as_dict())
