from src.presentation.http.common.contract import Contract

from .auth import Fingerprint, Login, Register, Token, VerificationCode
from .pagination import OffsetPagination
from .role import Role
from .status import Status
from .user import AdminUpdateUser, SelectUsers, UpdateSelf, User

__all__ = (
    "AdminUpdateUser",
    "Contract",
    "Fingerprint",
    "Login",
    "OffsetPagination",
    "OffsetResult",
    "Register",
    "Role",
    "SelectUsers",
    "Status",
    "Token",
    "UpdateSelf",
    "User",
    "VerificationCode",
)


class OffsetResult[T](Contract):
    data: list[T]
    offset: int = 0
    limit: int | None = None
    total: int
