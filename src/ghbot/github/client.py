import asyncio
import http
from collections.abc import Mapping
from contextlib import asynccontextmanager

import gidgethub
import httpx

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.log import get_logger
from ghbot.rate_limit import RateLimitGate

_RETRY_DELAY = 1.0
_FALLBACK_RATE_LIMIT_DELAY = 60
_RETRYABLE = (gidgethub.GitHubBroken, httpx.TransportError)
_SECONDARY_RATE_LIMIT_MESSAGE = "You have exceeded a secondary rate limit."


def _retry_after(response: object) -> int | None:
    """Return GitHub's integer Retry-After value when one is available."""
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return None
    value = headers.get("Retry-After") or headers.get("retry-after")
    try:
        delay = int(value)
    except (TypeError, ValueError):
        return None
    return delay if delay >= 0 else None


@asynccontextmanager
async def github_api_call(gh):
    log = get_logger("ghbot.requests")
    log.debug("github api call starting")
    try:
        gate = getattr(gh, "rate_limit_gate", None)
        if isinstance(gate, RateLimitGate):
            await gate.wait()
        yield
        log.debug("github api call completed")
    except _RETRYABLE as e:
        await asyncio.sleep(_RETRY_DELAY)
        raise GitHubApiError(str(e)) from e
    except gidgethub.RateLimitExceeded as e:
        reset_at = getattr(getattr(e, "rate_limit", None), "reset_datetime", None)
        delay = _retry_after(e)
        raise GitHubPrimaryRateLimitError(
            str(e),
            delay_seconds=(
                delay
                if delay is not None
                else _FALLBACK_RATE_LIMIT_DELAY
                if reset_at is None
                else None
            ),
            reset_at=reset_at,
        ) from e
    except gidgethub.GraphQLException as e:
        if _is_secondary_graphql_rate_limit(e):
            raise GitHubSecondaryRateLimitError(
                str(e), delay_seconds=_FALLBACK_RATE_LIMIT_DELAY
            ) from e
        if _is_primary_graphql_rate_limit(gh, e):
            reset_at = getattr(getattr(gh, "rate_limit", None), "reset_datetime", None)
            raise GitHubPrimaryRateLimitError(
                str(e),
                delay_seconds=_FALLBACK_RATE_LIMIT_DELAY if reset_at is None else None,
                reset_at=reset_at,
            ) from e
        raise GitHubApiError(str(e)) from e
    except gidgethub.HTTPException as e:
        if e.status_code == http.HTTPStatus.NOT_FOUND:
            raise GitHubNotFoundError(str(e)) from e
        if e.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
            delay = _retry_after(e)
            raise GitHubSecondaryRateLimitError(
                str(e),
                delay_seconds=_FALLBACK_RATE_LIMIT_DELAY if delay is None else delay,
            ) from e
        if e.status_code == http.HTTPStatus.FORBIDDEN:
            if "secondary rate limit" in str(e).lower():
                delay = _retry_after(e)
                raise GitHubSecondaryRateLimitError(
                    str(e),
                    delay_seconds=_FALLBACK_RATE_LIMIT_DELAY
                    if delay is None
                    else delay,
                ) from e
            raise GitHubNotFoundError(str(e)) from e  # access denied — skip
        raise GitHubApiError(str(e)) from e


def _graphql_error_codes(error: gidgethub.GraphQLException) -> set[str]:
    response = error.response
    if not isinstance(response, dict):
        return set()
    errors = response.get("errors")
    if not isinstance(errors, list):
        return set()
    values: list[object] = []
    for details in errors:
        if not isinstance(details, dict):
            continue
        extensions = details.get("extensions")
        values.append(details.get("type"))
        if isinstance(extensions, dict):
            values.extend((extensions.get("code"), extensions.get("type")))
    return {value.upper() for value in values if isinstance(value, str)}


def _is_secondary_graphql_rate_limit(error: gidgethub.GraphQLException) -> bool:
    codes = _graphql_error_codes(error)
    if any("SECONDARY" in code and "RATE" in code for code in codes):
        return True
    return str(error) == _SECONDARY_RATE_LIMIT_MESSAGE


def _is_primary_graphql_rate_limit(gh, error: gidgethub.GraphQLException) -> bool:
    codes = _graphql_error_codes(error)
    if codes & {"RATE_LIMITED", "RATE_LIMIT_EXCEEDED", "PRIMARY_RATE_LIMITED"}:
        return True
    rate_limit = getattr(gh, "rate_limit", None)
    return getattr(rate_limit, "remaining", None) == 0
