from typing import Literal, TypedDict

from uuid_utils.compat import UUID

UserLoads = Literal["role"]


class CreateUserType(TypedDict):
    login: str
    password: str
    role_uuid: UUID


class UpdateUserType(TypedDict, total=False):
    login: str | None
    password: str | None
    role_uuid: UUID | None
