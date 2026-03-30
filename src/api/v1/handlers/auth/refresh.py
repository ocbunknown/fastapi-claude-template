from dataclasses import dataclass

from src.api.common.dto.base import DTO
from src.api.common.interfaces.handler import Handler
from src.api.v1 import dtos
from src.common.exceptions import UnAuthorizedError
from src.services import InternalServiceGateway
from src.services.internal.auth import TokensExpire


class RefreshTokenQuery(DTO):
    data: dtos.Fingerprint
    refresh_token: str


@dataclass(slots=True)
class RefreshTokenHandler(Handler[RefreshTokenQuery, TokensExpire]):
    internal_gateway: InternalServiceGateway

    async def __call__(self, query: RefreshTokenQuery) -> TokensExpire:
        if not (refresh_token := query.refresh_token):
            raise UnAuthorizedError("Not allowed")

        return await self.internal_gateway.auth.verify_refresh(
            query.data.fingerprint, refresh_token
        )
