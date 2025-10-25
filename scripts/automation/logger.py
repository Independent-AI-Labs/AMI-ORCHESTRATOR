"""Structured logging for auditability."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .config import get_config


class JSONFormatter(logging.Formatter):
    """Format logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger wrapper."""

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        self._setup()

    def _setup(self) -> None:
        """Setup logger with JSON formatter."""
        if self.logger.handlers:
            return  # Already configured

        config = get_config()
        level = config.get("logging.level", "INFO")
        self.logger.setLevel(level)

        # Console handler (JSON)
        console = logging.StreamHandler()
        console.setFormatter(JSONFormatter())
        self.logger.addHandler(console)

        # File handler (JSON, with rotation)
        try:
            log_dir = config.root / config.get("paths.logs") / self.logger.name
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / f"{datetime.now():%Y-%m-%d}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
        except Exception as e:
            # If file handler fails, continue with console only
            self.logger.warning(f"Could not create file handler: {e}")

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info with structured data.

        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        self._log("INFO", message, kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error with structured data.

        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        self._log("ERROR", message, kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning with structured data.

        Args:
            message: Log message
            **kwargs: Additional structured fields
        """
        self._log("WARNING", message, kwargs)

    def _log(self, level: str, message: str, extra: dict[str, Any]) -> None:
        """Log with extra fields.

        Args:
            level: Log level (INFO, ERROR, WARNING)
            message: Log message
            extra: Extra structured fields
        """
        record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level),
            pathname="",
            lineno=0,
            msg=message,
            args=(),
            exc_info=None,
        )
        # Store extra fields in record.__dict__ to avoid type: ignore
        record.__dict__["extra_fields"] = extra
        self.logger.handle(record)


def get_logger(name: str) -> StructuredLogger:
    """Get or create structured logger.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
