from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import orjson

from .connection import ConnectionMetadata


class Response:
    def __init__(
        self,
        response: str | bytes,
    ) -> None:
        self._raw_response = response

    def raw(self) -> str | bytes:
        return self._raw_response

    def read(self) -> bytes:
        if isinstance(self._raw_response, bytes):
            return self._raw_response
        return self._raw_response.encode()

    def text(self) -> str:
        return str(self._raw_response)

    def json(self) -> Any:
        if isinstance(self._raw_response, str | bytes | bytearray):
            return orjson.loads(self._raw_response)
        raise TypeError("Raw message data is not deserializable")


@dataclass
class RawMessage:
    data: Response
    connection_id: str
    timestamp: float
    metadata: Optional[ConnectionMetadata] = None
