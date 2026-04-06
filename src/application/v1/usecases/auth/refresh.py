from dataclasses import dataclass

from src.application.common.exceptions import UnAuthorizedError
from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.services import ServiceGateway
from src.application.v1.services.auth import TokensExpire


class RefreshTokenRequest(Request):
    fingerprint: str
    refresh_token: str


@dataclass(slots=True)
class RefreshTokenUseCase(UseCase[RefreshTokenRequest, TokensExpire]):
    services: ServiceGateway

    async def __call__(self, request: RefreshTokenRequest) -> TokensExpire:
        if not (refresh_token := request.refresh_token):
            raise UnAuthorizedError("Not allowed")

        return await self.services.auth.verify_refresh(
            request.fingerprint, refresh_token
        )
