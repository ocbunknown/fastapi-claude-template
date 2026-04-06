from collections.abc import Mapping
from typing import Any, Optional

from fastapi.responses import ORJSONResponse as _ORJSONResponse
from starlette.background import BackgroundTask

from src.presentation.http.common.serializers.orjson import orjson_dumps


class ORJSONResponse(_ORJSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson_dumps(content)


class OkResponse[ResultType](ORJSONResponse):
    __slots__ = ()

    def __init__(
        self,
        content: ResultType,
        status_code: int = 200,
        headers: Optional[Mapping[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[BackgroundTask] = None,
    ) -> None:
        super().__init__(content, status_code, headers, media_type, background)
