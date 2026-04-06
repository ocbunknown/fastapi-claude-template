from dataclasses import asdict
from typing import Any, Dict, Literal

from argon2 import Parameters, PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from argon2.profiles import (
    CHEAPEST,
    PRE_21_2,
    RFC_9106_HIGH_MEMORY,
    RFC_9106_LOW_MEMORY,
)

ProfileType = Literal[
    "RFC_9106_LOW_MEMORY", "RFC_9106_HIGH_MEMORY", "CHEAPEST", "PRE_21_2", "DEFAULT"
]
PROFILES: Dict[str, Parameters] = {
    "RFC_9106_LOW_MEMORY": RFC_9106_LOW_MEMORY,
    "RFC_9106_HIGH_MEMORY": RFC_9106_HIGH_MEMORY,
    "CHEAPEST": CHEAPEST,
    "PRE_21_2": PRE_21_2,
}


class Argon2:
    __slots__ = ("_hasher",)

    def __init__(self, hasher: PasswordHasher) -> None:
        self._hasher = hasher

    def hash_password(self, plain: str) -> str:
        return self._hasher.hash(plain)

    def verify_password(self, hashed: str, plain: str) -> bool:
        try:
            return self._hasher.verify(hashed, plain)
        except (VerificationError, VerifyMismatchError):
            return False


def get_argon2_hasher(profile: ProfileType = "DEFAULT", **kwargs: Any) -> Argon2:
    if profile == "DEFAULT":
        kw = {}
    else:
        kw = asdict(PROFILES[profile])
        kw.pop("version", None)

    return Argon2(PasswordHasher(**(kw | kwargs)))
