from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional, TypedDict


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionConfig:
    uri: str
    proxy: Optional[str] = None
    headers: Optional[dict[str, str]] = field(default_factory=dict)
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    max_connection_retries: int = 10
    ping_interval: Optional[int] = 20
    ping_timeout: Optional[int] = 10
    connection_timeout: Optional[int] = None
    subprotocols: Optional[list[str]] = field(default_factory=list)
    context: Optional[dict[str, Any]] = field(default_factory=dict)


class ConnectionMetadata(TypedDict):
    config: ConnectionConfig
    transport_id: str


@dataclass
class Connection:
    id: str
    uri: str
    state: ConnectionState
    reconnect_attempts: int = 0
    last_ping: Optional[float] = None
    metadata: Optional[ConnectionMetadata] = None
