from typing import Annotated

from pydantic import Field

from src.application.v1.constants import (
    MAX_LOGIN_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
)
from src.presentation.http.common.contract import Contract


class Fingerprint(Contract):
    fingerprint: str


class Login(Fingerprint):
    login: Annotated[
        str,
        Field(
            max_length=MAX_LOGIN_LENGTH,
            description=f"Login maximum length `{MAX_LOGIN_LENGTH}`",
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=MIN_PASSWORD_LENGTH,
            max_length=MAX_PASSWORD_LENGTH,
        ),
    ]


class Register(Fingerprint):
    login: Annotated[
        str,
        Field(
            max_length=MAX_LOGIN_LENGTH,
            description=f"Login maximum length `{MAX_LOGIN_LENGTH}`",
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=MIN_PASSWORD_LENGTH,
            max_length=MAX_PASSWORD_LENGTH,
            description=(
                f"Password between `{MIN_PASSWORD_LENGTH}` and "
                f"`{MAX_PASSWORD_LENGTH}` characters long"
            ),
        ),
    ]


class VerificationCode(Contract):
    code: str


class Token(Contract):
    token: str
