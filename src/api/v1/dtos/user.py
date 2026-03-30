from typing import Annotated

from pydantic import Field
from uuid_utils.compat import UUID

from src.api.common.dto.base import DTO
from src.api.v1.constants import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from src.api.v1.dtos.role import Role


class User(DTO):
    uuid: UUID
    login: str
    active: bool

    # relations
    role: Role | None = None


class PrivateUser(User):
    access_token: str
    refresh_token: str


class UpdateUser(DTO):
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
