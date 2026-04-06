from nats.aio.client import Client as NatsClient

from src.settings.core import Settings


async def create_nats_connection(client: NatsClient, settings: Settings) -> NatsClient:
    await client.connect(
        servers=settings.nats.servers,
        user=settings.nats.user or None,
        password=settings.nats.password or None,
    )
    return client
