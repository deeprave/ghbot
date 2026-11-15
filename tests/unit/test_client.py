import http
import logging
import logging.handlers
from unittest.mock import AsyncMock

import gidgethub
import httpx
import pytest

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call


def _graphql_query_error(
    message: str,
    *,
    error_type: str | None = None,
    additional_errors: tuple[dict[str, str], ...] = (),
) -> gidgethub.QueryError:
    error = {"message": message}
    if error_type is not None:
        error["type"] = error_type
    return gidgethub.QueryError({"errors": [error, *additional_errors]})


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
async def test_graphql_query_error_raises_github_api_error():
    gh = AsyncMock()
    with pytest.raises(GitHubApiError, match="invalid query"):
        async with github_api_call(gh):
            raise _graphql_query_error("invalid query")


@pytest.mark.anyio
async def test_graphql_rate_limit_error_raises_primary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubPrimaryRateLimitError, match="rate limit"):
        async with github_api_call(gh):
            raise _graphql_query_error(
                "API rate limit exceeded", error_type="RATE_LIMITED"
            )


@pytest.mark.anyio
async def test_graphql_secondary_rate_limit_error_raises_secondary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubSecondaryRateLimitError, match="secondary rate limit"):
        async with github_api_call(gh):
            raise _graphql_query_error(
                "You have exceeded a secondary rate limit.",
                error_type="SECONDARY_RATE_LIMITED",
            )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error_type", "exception_type"),
    [
        ("RATE_LIMITED", GitHubPrimaryRateLimitError),
        ("SECONDARY_RATE_LIMITED", GitHubSecondaryRateLimitError),
    ],
)
async def test_graphql_later_rate_limit_error_uses_rate_limit_policy(
    error_type, exception_type
):
    gh = AsyncMock()
    with pytest.raises(exception_type):
        async with github_api_call(gh):
            raise _graphql_query_error(
                "ordinary query failure",
                additional_errors=(
                    {"message": "rate limit exceeded", "type": error_type},
                ),
            )


@pytest.mark.anyio
async def test_graphql_documented_secondary_limit_message_raises_secondary_limit():
    gh = AsyncMock()
    with pytest.raises(GitHubSecondaryRateLimitError):
        async with github_api_call(gh):
            raise _graphql_query_error("You have exceeded a secondary rate limit.")


@pytest.mark.anyio
async def test_graphql_error_with_rate_limit_words_but_no_rate_limit_type_is_api_error():
    gh = AsyncMock()
    with pytest.raises(GitHubApiError, match="secondary rate limit") as error:
        async with github_api_call(gh):
            raise _graphql_query_error("the query mentions a secondary rate limit")
    assert type(error.value) is GitHubApiError


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
async def test_secondary_rate_limit_403_raises_secondary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubSecondaryRateLimitError):
        async with github_api_call(gh):
            raise gidgethub.BadRequest(
                http.HTTPStatus.FORBIDDEN,
                "You have exceeded a secondary rate limit.",
            )


@pytest.mark.anyio
async def test_github_api_call_logs_debug_lifecycle_on_requests_logger():
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
        assert len(debug_records) >= 2
        assert {record.name for record in debug_records} == {"ghbot.requests"}
    finally:
        requests_logger.removeHandler(handler)
        requests_logger.setLevel(logging.NOTSET)
