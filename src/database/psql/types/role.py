from typing import Literal, TypedDict

from src.database.psql.models.types import Roles

RoleLoads = Literal["users"]


class CreateRoleType(TypedDict):
    name: Roles
