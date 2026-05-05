import json
import logging
import sys
from datetime import datetime
from typing import Any, cast

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


class LoggerWithTrace(logging.Logger):
    def trace(self, message: Any, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, message, args, **kwargs)


logging.setLoggerClass(LoggerWithTrace)


def get_logger(name: str) -> LoggerWithTrace:
    return cast(LoggerWithTrace, logging.getLogger(name))


def get_log_level(level: str) -> int:
    if level.upper() == "TRACE":
        return TRACE_LEVEL
    return getattr(logging, level.upper(), logging.INFO)


class _TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )


class _SuppressRequestsFilter(logging.Filter):
    """Drops records from the ghbot.requests logger and httpx/httpcore transport loggers."""

    _SUPPRESSED = ("ghbot.requests", "httpx", "httpcore")

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(record.name.startswith(prefix) for prefix in self._SUPPRESSED)


def configure(
    console_level: str = "INFO",
    log_file: str | None = None,
    log_level: str = "INFO",
    json_format: bool = False,
    requests: bool = False,
) -> None:
    root = logging.getLogger()
    root.setLevel(TRACE_LEVEL)  # root captures everything; handlers filter
    root.handlers.clear()

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(get_log_level(console_level))
    console.setFormatter(_TextFormatter())
    if not requests:
        console.addFilter(_SuppressRequestsFilter())
    root.addHandler(console)

    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(get_log_level(log_level))
        fh.setFormatter(_JSONFormatter() if json_format else _TextFormatter())
        if not requests:
            fh.addFilter(_SuppressRequestsFilter())
        root.addHandler(fh)
