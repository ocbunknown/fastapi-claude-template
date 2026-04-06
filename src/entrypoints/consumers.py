import structlog
from dishka_faststream import FastStreamProvider, setup_dishka
from faststream import FastStream
from faststream.nats import NatsBroker as FaststreamNatsBroker
from faststream.security import SASLPlaintext

from src.consumers.routers import setup_subscribers_routers
from src.entrypoints.container import build_container
from src.infrastructure.broker.nats.serializer import decode_payload
from src.infrastructure.logging import setup_logging
from src.settings.core import Settings, load_settings

log = structlog.get_logger(__name__)


def create_consumers(settings: Settings) -> FastStream:
    log.info("Initialize consumers (FastStream) application")

    security = (
        SASLPlaintext(username=settings.nats.user, password=settings.nats.password)
        if settings.nats.user and settings.nats.password
        else None
    )

    broker = FaststreamNatsBroker(
        servers=settings.nats.servers,
        security=security,
        decoder=lambda msg: decode_payload(msg.body),
    )

    container = build_container(settings, FastStreamProvider())

    faststream = FastStream(broker, after_shutdown=[container.close])

    setup_dishka(container, faststream, auto_inject=True)
    setup_subscribers_routers(broker)

    return faststream


settings = load_settings()
setup_logging(settings)
app = create_consumers(settings)
