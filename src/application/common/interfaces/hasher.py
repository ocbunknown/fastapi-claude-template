from typing import Protocol, runtime_checkable


@runtime_checkable
class Hasher(Protocol):
    def hash_password(self, plain: str) -> str: ...
    def verify_password(self, hashed: str, plain: str) -> bool: ...
