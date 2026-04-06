from enum import StrEnum
from typing import Literal


class RoleTypeEnum(StrEnum):
    ADMIN = "Admin"
    USER = "User"


type Roles = Literal["Admin", "User"]
