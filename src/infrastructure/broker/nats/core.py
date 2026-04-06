from nats.aio.client import Client as NatsClient
from nats.js import JetStreamContext

from src.application.common.events import BrokerEvent, StreamEvent
from src.application.common.interfaces.broker import Broker
from src.infrastructure.broker.nats.message import (
    NatsJetStreamMessage,
    NatsMessage,
)
from src.infrastructure.broker.nats.serializer import encode_event


class NatsBroker(Broker[BrokerEvent, NatsMessage]):
    __slots__ = ("nats",)

    def __init__(self, nats: NatsClient) -> None:
        self.nats = nats

    async def publish(self, message: NatsMessage) -> None:
        await self.nats.publish(
            subject=message.subject,
            payload=message.payload,
            reply=message.reply,
            headers=message.headers or None,
        )

    def build_message(self, event: BrokerEvent) -> NatsMessage:
        return NatsMessage(
            subject=event.subject,
            payload=encode_event(event),
            headers=event._headers or {},
        )


class NatsJetStreamBroker(Broker[StreamEvent, NatsJetStreamMessage]):
    __slots__ = ("js",)

    def __init__(self, js: JetStreamContext) -> None:
        self.js = js

    async def publish(self, message: NatsJetStreamMessage) -> None:
        await self.js.publish(
            subject=message.subject,
            payload=message.payload,
            stream=message.stream,
            timeout=message.timeout,
            headers=message.headers or None,
        )

    def build_message(self, event: StreamEvent) -> NatsJetStreamMessage:
        return NatsJetStreamMessage(
            subject=event.subject,
            payload=encode_event(event),
            stream=event._stream,
            timeout=event._timeout,
            headers=event._headers or {},
        )
