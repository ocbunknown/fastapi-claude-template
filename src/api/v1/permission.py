from collections import namedtuple

from dishka.integrations.fastapi import inject
from fastapi import Request
from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param

from src.api.common.interfaces.mediator import Mediator
from src.api.v1 import dtos, handlers
from src.common.di import Depends
from src.common.exceptions import UnAuthorizedError
from src.database.models.types import Roles

Token = namedtuple("Token", ["access", "refresh"])


class Authorization(SecurityBase):
    def __init__(self, *permissions: Roles | None) -> None:
        self.model = HTTPBearerModel()
        self.scheme_name = type(self).__name__
        self._permission = permissions

    @inject
    async def __call__(
        self,
        request: Request,
        mediator: Depends[Mediator],
    ) -> dtos.PrivateUser:
        token = self._get_tokens(request)

        result: dtos.PrivateUser = await mediator.send(
            handlers.auth.PermissionQuery(
                permissions=self._permission,
                access_token=token.access,
                refresh_token=token.refresh,
            )
        )
        return result

    def _get_tokens(self, request: Request) -> Token:
        refresh_token = request.cookies.get("refresh_token", "")
        access_token = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(access_token)

        if not (access_token and scheme and token):
            raise UnAuthorizedError("Not authenticated")
        if scheme.lower() != "bearer":
            raise UnAuthorizedError("Invalid authentication credentials")

        return Token(access=token, refresh=refresh_token)
