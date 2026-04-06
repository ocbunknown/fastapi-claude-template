from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.application.common.exceptions import UnAuthorizedError
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.results import StatusResult
from src.application.v1.services import ServiceGateway


class LogoutRequest(Request):
    user_uuid: uuid.UUID
    refresh_token: str


@dataclass(slots=True)
class LogoutUseCase(UseCase[LogoutRequest, StatusResult]):
    services: ServiceGateway

    async def __call__(self, request: LogoutRequest) -> StatusResult:
        if not (refresh_token := request.refresh_token):
            raise UnAuthorizedError("Not allowed")

        result = await self.services.auth.invalidate_refresh(
            refresh_token, request.user_uuid
        )
        return StatusResult(status=result)
