from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from nats.aio.client import Client as NatsClient

from src.application.common.bus import EventBusImpl
from src.application.common.interfaces.event_bus import EventBus
from src.infrastructure.broker.nats import NatsBroker, NatsJetStreamBroker
from src.infrastructure.broker.nats.connection import create_nats_connection
from src.settings.core import Settings


class BrokerProvider(Provider):
    scope = Scope.APP

    @provide
    async def nats_broker(
        self, settings: Settings
    ) -> AsyncIterator[NatsBroker]:
        client = NatsClient()
        await create_nats_connection(client, settings)
        broker = NatsBroker(client)
        try:
            yield broker
        finally:
            if not client.is_closed:
                await client.drain()

    @provide
    def jetstream_broker(self, nats: NatsBroker) -> NatsJetStreamBroker:
        return NatsJetStreamBroker(nats.nats.jetstream())

    @provide
    def event_bus(
        self,
        nats: NatsBroker,
        jetstream: NatsJetStreamBroker,
    ) -> EventBus:
        return (
            EventBusImpl.builder()
            .brokers(nats, jetstream)
            .build()
        )
