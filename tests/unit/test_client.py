import http
import logging
import logging.handlers
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import gidgethub
import httpx
import pytest

from ghbot.errors import (
    GitHubApiError,
    GitHubForbiddenError,
    GitHubGraphQLPartialDataError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import _retry_after, _secondary_reset_delay, github_api_call
from ghbot.rate_limit import RateLimitGate


def _graphql_query_error(
    message: str,
    *,
    error_type: str | None = None,
    additional_errors: tuple[dict[str, str], ...] = (),
    data: dict[str, object] | None = None,
) -> gidgethub.QueryError:
    error = {"message": message}
    if error_type is not None:
        error["type"] = error_type
    response: dict[str, object] = {"errors": [error, *additional_errors]}
    if data is not None:
        response["data"] = data
    return gidgethub.QueryError(response)


def test_retry_after_parses_a_response_header_and_rejects_invalid_values():
    assert (
        _retry_after(type("Response", (), {"headers": {"Retry-After": "42"}})()) == 42
    )


def test_secondary_reset_delay_uses_only_exhausted_quota_headers():
    response = type(
        "Response",
        (),
        {"headers": {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "0"}},
    )()

    assert _secondary_reset_delay(response) == 0
    assert (
        _retry_after(type("Response", (), {"headers": {"Retry-After": "no"}})()) is None
    )


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
async def test_graphql_field_error_with_data_preserves_partial_response():
    gh = AsyncMock()
    data = {"repository": {"visibility": "PRIVATE"}}

    with pytest.raises(GitHubGraphQLPartialDataError) as raised:
        async with github_api_call(gh):
            raise _graphql_query_error(
                "Resource not accessible by integration",
                error_type="FORBIDDEN",
                data=data,
            )

    assert raised.value.data == data
    assert raised.value.errors == (
        {
            "message": "Resource not accessible by integration",
            "type": "FORBIDDEN",
        },
    )


@pytest.mark.anyio
async def test_graphql_rate_limit_with_data_remains_fatal():
    with pytest.raises(GitHubPrimaryRateLimitError):
        async with github_api_call(AsyncMock()):
            raise _graphql_query_error(
                "API rate limit exceeded",
                error_type="RATE_LIMITED",
                data={"repository": {"visibility": "PRIVATE"}},
            )


@pytest.mark.anyio
async def test_graphql_rate_limit_error_raises_primary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubPrimaryRateLimitError, match="rate limit"):
        async with github_api_call(gh):
            raise _graphql_query_error(
                "API rate limit exceeded", error_type="RATE_LIMITED"
            )


@pytest.mark.anyio
async def test_graphql_primary_limit_uses_the_available_reset_time():
    reset_at = datetime.now(UTC) + timedelta(hours=1)
    gh = SimpleNamespace(
        rate_limit=SimpleNamespace(remaining=0, reset_datetime=reset_at)
    )

    with pytest.raises(GitHubPrimaryRateLimitError) as raised:
        async with github_api_call(gh):
            raise _graphql_query_error(
                "API rate limit exceeded", error_type="RATE_LIMITED"
            )

    assert raised.value.delay_seconds is None
    assert raised.value.reset_at == reset_at


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
    with pytest.raises(GitHubPrimaryRateLimitError) as raised:
        async with github_api_call(gh):
            raise gidgethub.RateLimitExceeded(rate_limit=None)

    assert raised.value.delay_seconds == 60
    assert raised.value.reset_at is None


@pytest.mark.anyio
async def test_primary_limit_prefers_retry_after_over_reset_time():
    gh = AsyncMock()
    error = gidgethub.RateLimitExceeded(
        rate_limit=SimpleNamespace(
            reset_datetime=datetime.now(UTC) + timedelta(hours=1)
        )
    )
    error.headers = {"Retry-After": "7"}

    with pytest.raises(GitHubPrimaryRateLimitError) as raised:
        async with github_api_call(gh):
            raise error

    assert raised.value.delay_seconds == 7


@pytest.mark.anyio
async def test_timingless_rest_and_graphql_limits_share_the_fallback_gate():
    now = 10.0
    waits: list[float] = []

    async def sleep(delay: float) -> None:
        nonlocal now
        waits.append(delay)
        now += delay

    gate = RateLimitGate(
        max_wait=120,
        max_hits=1,
        clock=lambda: now,
        sleep=sleep,
        retry_jitter=lambda: 0,
    )
    gh = SimpleNamespace(rate_limit_gate=gate)

    with pytest.raises(GitHubPrimaryRateLimitError) as rest_error:
        async with github_api_call(gh):
            raise gidgethub.RateLimitExceeded(rate_limit=None)
    assert rest_error.value.delay_seconds == 60
    assert await gate.record(rest_error.value)

    with pytest.raises(GitHubPrimaryRateLimitError) as graphql_error:
        async with github_api_call(SimpleNamespace()):
            raise _graphql_query_error(
                "API rate limit exceeded", error_type="RATE_LIMITED"
            )
    assert graphql_error.value.delay_seconds == 60
    assert await gate.record(graphql_error.value)

    assert gate.hits == 1
    async with github_api_call(gh):
        pass
    assert waits == [60]


@pytest.mark.anyio
async def test_429_raises_secondary_rate_limit_error():
    gh = AsyncMock()
    with pytest.raises(GitHubSecondaryRateLimitError) as raised:
        async with github_api_call(gh):
            raise gidgethub.BadRequest(http.HTTPStatus.TOO_MANY_REQUESTS)

    assert raised.value.delay_seconds == 60


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "message", "error_type"),
    [
        (
            http.HTTPStatus.TOO_MANY_REQUESTS,
            "too many requests",
            GitHubSecondaryRateLimitError,
        ),
        (
            http.HTTPStatus.FORBIDDEN,
            "You have exceeded a secondary rate limit. Wait.",
            GitHubSecondaryRateLimitError,
        ),
        (
            http.HTTPStatus.FORBIDDEN,
            "API rate limit exceeded",
            GitHubPrimaryRateLimitError,
        ),
    ],
)
async def test_bad_graphql_request_rate_limits_are_normalized(
    status, message, error_type
):
    with pytest.raises(error_type):
        async with github_api_call(AsyncMock()):
            raise gidgethub.BadGraphQLRequest(status, {"message": message})


@pytest.mark.anyio
async def test_bad_graphql_request_403_raises_forbidden_error():
    with pytest.raises(GitHubForbiddenError, match="Resource not accessible") as raised:
        async with github_api_call(AsyncMock()):
            raise gidgethub.BadGraphQLRequest(
                http.HTTPStatus.FORBIDDEN,
                {"message": "Resource not accessible by integration"},
            )

    assert type(raised.value) is GitHubForbiddenError


@pytest.mark.anyio
async def test_bad_graphql_request_404_raises_not_found_error():
    with pytest.raises(GitHubNotFoundError, match="Not Found") as raised:
        async with github_api_call(AsyncMock()):
            raise gidgethub.BadGraphQLRequest(
                http.HTTPStatus.NOT_FOUND, {"message": "Not Found"}
            )

    assert type(raised.value) is GitHubNotFoundError


@pytest.mark.anyio
async def test_graphql_forbidden_code_raises_forbidden_error():
    with pytest.raises(GitHubForbiddenError, match="Forbidden") as raised:
        async with github_api_call(AsyncMock()):
            raise _graphql_query_error("Forbidden", error_type="FORBIDDEN")

    assert type(raised.value) is GitHubForbiddenError


@pytest.mark.anyio
async def test_403_plain_raises_forbidden_error():
    gh = AsyncMock()
    with pytest.raises(GitHubForbiddenError, match="Forbidden") as raised:
        async with github_api_call(gh):
            raise gidgethub.BadRequest(http.HTTPStatus.FORBIDDEN)

    assert type(raised.value) is GitHubForbiddenError


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
