from __future__ import annotations

from uuid_utils.compat import UUID

from src.api.common.dto.base import DTO


class Role(DTO):
    uuid: UUID
    name: str
