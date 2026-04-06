from typing import Any

import msgpack  # type: ignore[import-untyped]

from src.application.common.events import BrokerEvent


def encode_event(event: BrokerEvent) -> bytes:
    return msgpack.packb(  # type: ignore[no-any-return]
        event.model_dump(
            mode="json",
            exclude={"subject"},
            by_alias=True,
            exclude_none=True,
        )
    )


def decode_payload(payload: bytes) -> Any:
    return msgpack.unpackb(payload)
