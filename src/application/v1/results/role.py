import uuid_utils.compat as uuid

from src.application.v1.results.base import Result


class RoleResult(Result):
    uuid: uuid.UUID
    name: str
