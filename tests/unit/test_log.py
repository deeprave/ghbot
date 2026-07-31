import json
import logging
import logging.handlers
from datetime import UTC, datetime

import pytest

from ghbot.log import _JSONFormatter, _SuppressRequestsFilter, configure


@pytest.fixture(autouse=True)
def reset_root_logger():
    yield
    logging.getLogger().handlers.clear()


def _get_console_handler() -> logging.StreamHandler | None:
    """Return the first StreamHandler on the root logger, or None."""
    for h in logging.getLogger().handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(
            h, logging.FileHandler
        ):
            return h
    return None


def test_configure_suppresses_requests_on_console_by_default():
    """Without --requests, the console handler has a filter that drops ghbot.requests records."""
    configure()
    handler = _get_console_handler()
    assert handler is not None
    assert any(isinstance(f, _SuppressRequestsFilter) for f in handler.filters)


def test_configure_no_suppress_when_requests_flag_set():
    """With --requests=True, the console handler has no SuppressRequestsFilter."""
    configure(requests=True)
    handler = _get_console_handler()
    assert handler is not None
    assert not any(isinstance(f, _SuppressRequestsFilter) for f in handler.filters)


def test_suppress_filter_blocks_requests_records():
    """_SuppressRequestsFilter drops records from ghbot.requests and its children."""
    f = _SuppressRequestsFilter()
    for name in ("ghbot.requests", "httpx", "httpcore", "httpcore.connection"):
        record = logging.LogRecord(
            name=name,
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is False, f"Expected {name!r} to be suppressed"


def test_suppress_filter_passes_other_records():
    """_SuppressRequestsFilter passes records from other loggers."""
    f = _SuppressRequestsFilter()
    record = logging.LogRecord(
        name="ghbot.processor",
        level=logging.DEBUG,
        pathname="",
        lineno=0,
        msg="test",
        args=(),
        exc_info=None,
    )
    assert f.filter(record) is True


def test_json_formatter_uses_utc_timestamp():
    record = logging.LogRecord(
        name="ghbot.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="test",
        args=(),
        exc_info=None,
    )
    record.created = 0

    payload = json.loads(_JSONFormatter().format(record))

    assert payload["timestamp"] == datetime.fromtimestamp(0, UTC).isoformat()
