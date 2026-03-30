from typing import Protocol, runtime_checkable


@runtime_checkable
class Encrypt(Protocol):
    def encrypt(self, plain: str) -> str: ...
    def decrypt(self, encrypted: str) -> str: ...
