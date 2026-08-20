"""Centralized logging configuration for the application."""

import logging
import sys

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with a single, consistent console handler.

    Safe to call multiple times: an existing stream handler is reused and only
    the level is updated, so tests and multiple app reloads do not duplicate
    handlers.
    """
    log_level = level.upper()

    root = logging.getLogger()
    root.setLevel(log_level)

    if not any(
        isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout
        for handler in root.handlers
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setFormatter(
                    logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
                )

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(log_level)