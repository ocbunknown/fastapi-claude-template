import base64
from datetime import UTC, datetime, timedelta
from typing import (
    Any,
    Literal,
    Optional,
    cast,
)

import jwt

from src.common.exceptions import ConflictError, UnAuthorizedError
from src.settings.core import CipherSettings

TokenType = Literal["access", "refresh"]


class JWT:
    __slots__ = ("_settings",)

    def __init__(self, settings: CipherSettings) -> None:
        self._settings = settings

    def create(
        self,
        typ: TokenType,
        sub: str,
        expires_delta: Optional[timedelta] = None,
        **kw: Any,
    ) -> tuple[datetime, str]:
        now = datetime.now(UTC)
        if expires_delta:
            expire = now + expires_delta
        else:
            seconds_delta = (
                self._settings.access_token_expire_seconds
                if typ == "access"
                else self._settings.refresh_token_expire_seconds
            )
            expire = now + timedelta(seconds=seconds_delta)

        if now >= expire:
            raise ConflictError("Invalid expiration delta was provided")

        to_encode = {
            "exp": expire,
            "sub": sub,
            "iat": now,
            "type": typ,
        }
        try:
            token = jwt.encode(
                to_encode | kw,
                base64.b64decode(self._settings.secret_key),
                self._settings.algorithm,
            )
        except jwt.PyJWTError as e:
            raise UnAuthorizedError("Token is expired") from e

        return expire, token

    def verify_token(self, token: str) -> dict[str, Any]:
        try:
            result = jwt.decode(
                token,
                base64.b64decode(self._settings.public_key),
                [self._settings.algorithm],
            )
        except jwt.PyJWTError as e:
            raise UnAuthorizedError("Token is invalid or expired") from e

        return cast(dict[str, Any], result)
