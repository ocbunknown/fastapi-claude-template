import uuid_utils.compat as uuid

from src.application.v1.results.base import Result
from src.application.v1.results.role import RoleResult


class UserResult(Result):
    uuid: uuid.UUID
    login: str
    active: bool
    role: RoleResult | None = None
