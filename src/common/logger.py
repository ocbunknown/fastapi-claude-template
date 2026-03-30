import logging

from src.settings.core import (
    DATETIME_FORMAT,
    LOG_LEVEL,
    LOGGING_FORMAT,
    PROJECT_NAME,
)

logging.basicConfig(level=LOG_LEVEL, format=LOGGING_FORMAT, datefmt=DATETIME_FORMAT)

log = logging.getLogger(PROJECT_NAME)
