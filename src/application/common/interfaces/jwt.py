from datetime import datetime, timedelta
from typing import Any, Literal, Protocol, runtime_checkable

TokenType = Literal["access", "refresh"]


@runtime_checkable
class JWT(Protocol):
    def create(
        self,
        typ: TokenType,
        sub: str,
        expires_delta: timedelta | None = None,
        **kw: Any,
    ) -> tuple[datetime, str]: ...

    def verify_token(self, token: str) -> dict[str, Any]: ...
