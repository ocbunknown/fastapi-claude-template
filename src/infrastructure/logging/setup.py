import logging
import logging.config
import sys
from typing import Any

import orjson
import structlog
from structlog.types import EventDict, Processor

from src.settings.core import Settings


def _orjson_dumps(value: Any, *, default: Any) -> str:
    return orjson.dumps(value, default=default).decode()


def _drop_color_message_key(
    _: logging.Logger, __: str, event_dict: EventDict
) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def setup_logging(settings: Settings) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        _drop_color_message_key,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.app.log_level.upper()]
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    final_processors: list[Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    ]
    if settings.app.production:
        final_processors.append(
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
            )
        )
        final_processors.append(
            structlog.processors.JSONRenderer(serializer=_orjson_dumps)
        )
    else:
        final_processors.append(structlog.dev.ConsoleRenderer(colors=True))

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=final_processors,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.app.log_level.upper())

    _tame_noisy_loggers()

    logging.captureWarnings(True)


def _tame_noisy_loggers() -> None:
    for name, level in {
        "uvicorn": logging.INFO,
        "uvicorn.error": logging.INFO,
        "uvicorn.access": logging.WARNING,
        "granian": logging.INFO,
        "granian.access": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "aiosqlite": logging.WARNING,
        "asyncio": logging.WARNING,
        "httpx": logging.WARNING,
        "aiohttp.access": logging.WARNING,
    }.items():
        lg = logging.getLogger(name)
        lg.setLevel(level)
        lg.handlers.clear()
        lg.propagate = True
