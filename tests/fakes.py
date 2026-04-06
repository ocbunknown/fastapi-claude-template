from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class FakeStrCache:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        expire: float | timedelta | None = None,
        **kw: Any,
    ) -> None:
        self._store[key] = str(value)

    async def setnx(
        self, key: str, value: Any, expire: float | timedelta | None = None
    ) -> bool:
        if key in self._store:
            return False
        self._store[key] = str(value)
        return True

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._store.pop(key, None)
            self._lists.pop(key, None)

    async def get_list(self, key: str) -> list[str]:
        return list(self._lists.get(key, []))

    async def set_list(
        self,
        key: str,
        *values: Any,
        expire: float | timedelta | None = None,
        **kw: Any,
    ) -> None:
        bucket = self._lists.setdefault(key, [])
        for value in values:
            bucket.insert(0, str(value))

    async def discard(self, key: str, value: Any, **kw: Any) -> None:
        bucket = self._lists.get(key)
        if not bucket:
            return
        self._lists[key] = [item for item in bucket if item != str(value)]

    async def exists(self, key: str) -> bool:
        return key in self._store or key in self._lists

    async def keys(self, pattern: str | None = None) -> list[str]:
        return list(self._store.keys()) + list(self._lists.keys())

    async def clear(self) -> None:
        self._store.clear()
        self._lists.clear()

    async def close(self) -> None:
        await self.clear()


class FakeHasher:
    PREFIX = "fake-hash:"

    def hash_password(self, plain: str) -> str:
        return f"{self.PREFIX}{plain}"

    def verify_password(self, hashed: str, plain: str) -> bool:
        return hashed == f"{self.PREFIX}{plain}"


class FakeJWT:
    PREFIX = "fake-jwt:"

    def create(
        self,
        typ: str,
        sub: str,
        expires_delta: timedelta | None = None,
        **kw: Any,
    ) -> tuple[datetime, str]:
        expire = datetime.now(UTC) + (expires_delta or timedelta(hours=1))
        token = f"{self.PREFIX}{typ}:{sub}"
        return expire, token

    def verify_token(self, token: str) -> dict[str, Any]:
        if not token.startswith(self.PREFIX):
            raise ValueError("Not a fake JWT token")
        _, typ, sub = token.split(":", 2)
        return {"type": typ, "sub": sub, "iat": datetime.now(UTC)}
