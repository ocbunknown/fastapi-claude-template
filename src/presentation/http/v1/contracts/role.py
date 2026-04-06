from __future__ import annotations

from uuid_utils.compat import UUID

from src.presentation.http.common.contract import Contract


class Role(Contract):
    uuid: UUID
    name: str
