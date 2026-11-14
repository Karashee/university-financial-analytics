"""Application-wide logging configuration (standard library only)."""
import logging
import sys

from app.config import settings
from app.core.db_log_handler import PostgresLogHandler

FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

# The audit handler is attached to this logger only - never the root logger -
# so uvicorn and SQLAlchemy chatter stays out of the system_logs table.
APP_LOGGER_NAME = "app"


def configure_logging() -> None:
    """Configure the root logger with a single StreamHandler and FORMAT."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FORMAT))

    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    _attach_db_log_handler()


def _attach_db_log_handler() -> None:
    """
    Attach the PostgreSQL audit handler to the "app" logger.

    Records from app.* loggers propagate through this logger, so one handler
    here captures the whole application without touching the root logger.
    Attaching is idempotent: running setup twice leaves a single handler.
    """
    if not settings.db_logging_enabled:
        return

    app_logger = logging.getLogger(APP_LOGGER_NAME)
    if any(isinstance(h, PostgresLogHandler) for h in app_logger.handlers):
        return

    app_logger.addHandler(PostgresLogHandler(level=logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name."""
    return logging.getLogger(name)


configure_logging()
