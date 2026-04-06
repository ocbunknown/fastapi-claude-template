from dishka.integrations.fastapi import inject
from fastapi import Request
from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.security.base import SecurityBase
from fastapi.security.utils import get_authorization_scheme_param

from src.application.common.exceptions import UnAuthorizedError
from src.application.common.interfaces.mediator import Mediator
from src.application.v1.results import UserResult
from src.application.v1.usecases.auth import PermissionRequest
from src.common.di import Depends
from src.database.psql.models.types import Roles


class Authorization(SecurityBase):
    def __init__(self, *roles: Roles) -> None:
        self.model = HTTPBearerModel()
        self.scheme_name = (
            type(self).__name__
            if not roles
            else f"{type(self).__name__}({','.join(roles)})"
        )
        self._roles = roles

    @inject
    async def __call__(
        self,
        request: Request,
        mediator: Depends[Mediator],
    ) -> UserResult:
        token = self._extract_bearer(request)
        return await mediator.send(
            PermissionRequest(access_token=token, permissions=self._roles)
        )

    def _extract_bearer(self, request: Request) -> str:
        header = request.headers.get("Authorization")
        scheme, token = get_authorization_scheme_param(header)
        if not (header and scheme and token):
            raise UnAuthorizedError("Not authenticated")
        if scheme.lower() != "bearer":
            raise UnAuthorizedError("Invalid authentication credentials")
        return token
