from typing import Any

from granian.constants import Interfaces
from granian.server import Server as Granian

from src.api.server.utils import workers_count
from src.common.logger import log
from src.settings.core import ServerSettings


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
        log_access=settings.log,
        interface=Interfaces.ASGI,
        **kwargs,
    )
    log.info("Running API Granian")
    server.serve()
