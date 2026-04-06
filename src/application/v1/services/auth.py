from dataclasses import dataclass
from datetime import datetime
from typing import Final

import uuid_utils.compat as uuid

from src.application.common.exceptions import ForbiddenError
from src.application.common.interfaces.cache import StrCache
from src.application.common.interfaces.jwt import JWT, TokenType

DEFAULT_TOKENS_COUNT: Final[int] = 5


@dataclass(slots=True)
class Token:
    token: str


@dataclass(slots=True)
class Tokens:
    access: str
    refresh: str


@dataclass(slots=True)
class TokensExpire:
    refresh_expire: datetime
    tokens: Tokens


class AuthService:
    __slots__ = ("_jwt", "_cache")

    def __init__(self, jwt: JWT, cache: StrCache) -> None:
        self._jwt = jwt
        self._cache = cache

    async def login(self, fingerprint: str, user_uuid: uuid.UUID) -> TokensExpire:
        _, access = self._jwt.create(typ="access", sub=str(user_uuid))
        expire, refresh = self._jwt.create(typ="refresh", sub=str(user_uuid))

        tokens = await self._cache.get_list(str(user_uuid))
        if len(tokens) > DEFAULT_TOKENS_COUNT:
            await self._cache.delete(str(user_uuid))

        await self._cache.set_list(str(user_uuid), f"{fingerprint}::{refresh}")

        return TokensExpire(
            refresh_expire=expire,
            tokens=Tokens(access=access, refresh=refresh),
        )

    async def verify_refresh(
        self,
        fingerprint: str,
        refresh_token: str,
    ) -> TokensExpire:
        user_uuid = await self.verify_token(refresh_token, "refresh")
        token_pairs = await self._cache.get_list(str(user_uuid))
        verified = None
        for pair in token_pairs:
            data = pair.split("::")
            if len(data) < 2:
                await self._cache.delete(str(user_uuid))
                raise ForbiddenError(
                    "Broken separator, try to login again. Token is not valid anymore"
                )
            fp, cached_token, *_ = data
            if fp == fingerprint and cached_token == refresh_token:
                verified = pair
                break

        if not verified:
            await self._cache.delete(str(user_uuid))
            raise ForbiddenError("Token is not valid anymore")

        await self._cache.discard(str(user_uuid), verified)

        _, access = self._jwt.create(typ="access", sub=str(user_uuid))
        expire, refresh = self._jwt.create(typ="refresh", sub=str(user_uuid))

        await self._cache.set_list(str(user_uuid), f"{fingerprint}::{refresh}")

        return TokensExpire(
            refresh_expire=expire,
            tokens=Tokens(access=access, refresh=refresh),
        )

    async def invalidate_refresh(
        self,
        refresh_token: str,
        user_uuid: uuid.UUID,
    ) -> bool:
        await self.verify_token(refresh_token, "refresh")
        token_pairs = await self._cache.get_list(str(user_uuid))
        for pair in token_pairs:
            data = pair.split("::")
            if len(data) < 2:
                await self._cache.delete(str(user_uuid))
                break
            _, cached_token, *_ = data
            if cached_token == refresh_token:
                await self._cache.discard(str(user_uuid), pair)
                break

        return True

    async def verify_token(
        self,
        token: str,
        token_type: TokenType,
    ) -> uuid.UUID:
        payload = self._jwt.verify_token(token)
        actual_token_type = payload.get("type")
        user_id = payload.get("sub")

        if actual_token_type != token_type:
            raise ForbiddenError("Invalid token")

        return uuid.UUID(user_id)
