from dataclasses import dataclass, field
from typing import Any

from src.application.common.interfaces.broker import BrokerMessage


@dataclass
class NatsMessage(BrokerMessage):
    subject: str = ""
    payload: bytes = b""
    reply: str = ""
    headers: dict[str, Any] = field(default_factory=dict)


@dataclass
class NatsJetStreamMessage(BrokerMessage):
    subject: str = ""
    payload: bytes = b""
    stream: str | None = None
    timeout: float | None = None
    headers: dict[str, Any] = field(default_factory=dict)
