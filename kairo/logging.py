"""Logging configuration for kairo-fetch."""

import sys

from loguru import logger

logger.remove()

logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    colorize=True,
)

log = logger
