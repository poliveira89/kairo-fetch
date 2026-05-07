"""Logging configuration for kairo-fetch."""

import sys

from loguru import logger

log = logger


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration for the application.

    This should be called by the application's entry point to avoid
    interfering with other libraries that may use loguru.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to INFO.
    """
    logger.remove()

    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level=level,
        colorize=True,
    )
