from typing import Annotated

import uuid_utils.compat as uuid
from pydantic import Field

from src.application.v1.constants import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from src.presentation.http.common.contract import Contract
from src.presentation.http.v1.contracts.role import Role


class User(Contract):
    uuid: uuid.UUID
    login: str
    active: bool

    role: Role | None = None


class SelectUsers(Contract):
    login: str | None = None
    role_uuid: uuid.UUID | None = None


class UpdateSelf(Contract):
    password: (
        Annotated[
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
        | None
    ) = None


class AdminUpdateUser(Contract):
    password: (
        Annotated[
            str,
            Field(
                min_length=MIN_PASSWORD_LENGTH,
                max_length=MAX_PASSWORD_LENGTH,
            ),
        ]
        | None
    ) = None
    role_uuid: uuid.UUID | None = None
    active: bool | None = None
