from typing import Any

import structlog
from granian.constants import Interfaces
from granian.server import Server as Granian

from src.entrypoints.server.utils import workers_count
from src.settings.core import ServerSettings

log = structlog.get_logger(__name__)


def run_api_granian(
    target: Any,
    settings: ServerSettings,
    **kwargs: Any,
) -> None:
    server = Granian(
        target,
        address=settings.host,
        port=settings.port,
        workers=settings.workers if settings.workers != "auto" else workers_count(),
        runtime_threads=settings.threads,
        log_access=False,
        interface=Interfaces.ASGI,
        factory=True,
        **kwargs,
    )
    log.info("Running API Granian")
    server.serve()
