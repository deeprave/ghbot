import http
import logging
import logging.handlers
import pytest
from unittest.mock import AsyncMock

import gidgethub
import httpx

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call


@pytest.mark.anyio
async def test_404_raises_not_found_error():
    gh = AsyncMock()
    with pytest.raises(GitHubNotFoundError):
        async with github_api_call(gh):
            raise gidgethub.BadRequest(http.HTTPStatus.NOT_FOUND)


@pytest.mark.anyio
async def test_other_http_error_raises_github_api_error():
    gh = AsyncMock()
    with pytest.raises(GitHubApiError):
        async with github_api_call(gh):
            raise gidgethub.BadRequest(http.HTTPStatus.UNPROCESSABLE_ENTITY)


@pytest.mark.anyio
async def test_transport_error_sleeps_then_raises_github_api_error(monkeypatch):
    calls = []

    async def fake_sleep(_):
        calls.append("sleep")

    monkeypatch.setattr("ghbot.github.client.asyncio.sleep", fake_sleep)

    gh = AsyncMock()
    with pytest.raises(GitHubApiError):
        async with github_api_call(gh):
            raise httpx.TransportError("connection failed")

    assert calls == ["sleep"]


@pytest.mark.anyio
async def test_github_broken_sleeps_then_raises_github_api_error(monkeypatch):
    calls = []

    async def fake_sleep(_):
        calls.append("sleep")

    monkeypatch.setattr("ghbot.github.client.asyncio.sleep", fake_sleep)

    gh = AsyncMock()
    with pytest.raises(GitHubApiError):
        async with github_api_call(gh):
            raise gidgethub.GitHubBroken(http.HTTPStatus.INTERNAL_SERVER_ERROR)

    assert calls == ["sleep"]


@pytest.mark.anyio
async def test_no_exception_passes_through():
    gh = AsyncMock()
    result = []
    async with github_api_call(gh):
        result.append("ok")
    assert result == ["ok"]


@pytest.mark.anyio
async def test_rate_limit_exceeded_raises_primary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubPrimaryRateLimitError):
        async with github_api_call(gh):
            raise gidgethub.RateLimitExceeded(rate_limit=None)


@pytest.mark.anyio
async def test_429_raises_secondary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubSecondaryRateLimitError):
        async with github_api_call(gh):
            raise gidgethub.BadRequest(http.HTTPStatus.TOO_MANY_REQUESTS)


@pytest.mark.anyio
async def test_403_plain_raises_not_found_error():
    gh = AsyncMock()
    with pytest.raises(GitHubNotFoundError):
        async with github_api_call(gh):
            raise gidgethub.BadRequest(http.HTTPStatus.FORBIDDEN)


@pytest.mark.anyio
async def test_github_api_call_logs_debug_on_entry():
    requests_logger = logging.getLogger("ghbot.requests")
    handler = logging.handlers.MemoryHandler(
        capacity=100, flushLevel=logging.CRITICAL + 1
    )
    requests_logger.addHandler(handler)
    requests_logger.setLevel(logging.DEBUG)
    try:
        gh = AsyncMock()
        async with github_api_call(gh):
            pass
        debug_records = [r for r in handler.buffer if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, "Expected at least one DEBUG record on entry"
    finally:
        requests_logger.removeHandler(handler)
        requests_logger.setLevel(logging.NOTSET)


@pytest.mark.anyio
async def test_github_api_call_logs_debug_on_exit():
    requests_logger = logging.getLogger("ghbot.requests")
    handler = logging.handlers.MemoryHandler(
        capacity=100, flushLevel=logging.CRITICAL + 1
    )
    requests_logger.addHandler(handler)
    requests_logger.setLevel(logging.DEBUG)
    try:
        gh = AsyncMock()
        async with github_api_call(gh):
            pass
        debug_records = [r for r in handler.buffer if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 2, (
            "Expected at least two DEBUG records (entry + exit)"
        )
    finally:
        requests_logger.removeHandler(handler)
        requests_logger.setLevel(logging.NOTSET)


@pytest.mark.anyio
async def test_github_api_call_logs_use_requests_logger():
    requests_logger = logging.getLogger("ghbot.requests")
    handler = logging.handlers.MemoryHandler(
        capacity=100, flushLevel=logging.CRITICAL + 1
    )
    requests_logger.addHandler(handler)
    requests_logger.setLevel(logging.DEBUG)
    try:
        gh = AsyncMock()
        async with github_api_call(gh):
            pass
        debug_records = [r for r in handler.buffer if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, "Expected at least one DEBUG record"
        for record in debug_records:
            assert record.name == "ghbot.requests", (
                f"Expected logger name 'ghbot.requests', got '{record.name}'"
            )
    finally:
        requests_logger.removeHandler(handler)
        requests_logger.setLevel(logging.NOTSET)
