from src.api.common.dto.base import DTO

from .auth import Fingerprint, Login, Register, VerificationCode
from .role import Role
from .status import Status
from .user import PrivateUser, UpdateUser, User

__all__ = (
    "User",
    "Register",
    "Fingerprint",
    "Login",
    "Role",
    "Status",
    "VerificationCode",
    "UpdateUser",
    "PrivateUser",
)


class OffsetResult[T](DTO):
    data: list[T]
    offset: int
    limit: int
    total: int
