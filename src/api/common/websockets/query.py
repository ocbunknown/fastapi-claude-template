from src.api.common.dto.base import DTO
from src.services.provider.websockets.datastructure.message import RawMessage


class WebsocketQuery(DTO):
    message: RawMessage
