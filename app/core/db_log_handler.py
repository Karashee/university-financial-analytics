"""PostgreSQL logging handler - persists application log records for audit."""
import logging
import threading
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.config import settings

# Reentrancy guard: SQLAlchemy emits its own log records while executing the
# INSERT below. Without this, a log write would trigger a log write, and so on.
_local = threading.local()

MAX_MESSAGE_LENGTH = 2000


class PostgresLogHandler(logging.Handler):
    """
    Write log records to the system_logs table.

    Uses its own engine with NullPool rather than the request-scoped session.
    This matters because the global SQLAlchemyError handler logs at ERROR while
    the request's own transaction is already in a failed state - reusing that
    session would mean the log write is rolled back with it, losing exactly the
    record that matters most.

    Every failure inside emit() is swallowed. Logging must never be able to
    break a request.
    """

    def __init__(self, level: int = logging.INFO) -> None:
        super().__init__(level)
        self._engine = create_engine(settings.database_url, poolclass=NullPool)

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(_local, "in_emit", False):
            return

        _local.in_emit = True
        try:
            message = record.getMessage()
            if record.exc_info:
                message = f"{message}\n{logging.Formatter().formatException(record.exc_info)}"

            with self._engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO system_logs
                            (logged_at, level, logger_name, message,
                             module, function_name, line_number)
                        VALUES
                            (:logged_at, :level, :logger_name, :message,
                             :module, :function_name, :line_number)
                        """
                    ),
                    {
                        "logged_at": datetime.fromtimestamp(record.created, tz=timezone.utc),
                        "level": record.levelname,
                        "logger_name": record.name,
                        "message": message[:MAX_MESSAGE_LENGTH],
                        "module": record.module,
                        "function_name": record.funcName,
                        "line_number": record.lineno,
                    },
                )
        except Exception:
            # Deliberately silent: a logging failure must not surface as a
            # request failure. Console logging still captures the record.
            pass
        finally:
            _local.in_emit = False
