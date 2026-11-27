import asyncio
import http
from collections.abc import Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import gidgethub
import httpx

from ghbot.errors import (
    GitHubApiError,
    GitHubForbiddenError,
    GitHubGraphQLPartialDataError,
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


def _header(headers: Mapping[object, object], name: str) -> str | None:
    """Look up a response header regardless of mapping key casing."""
    wanted = name.casefold()
    value = next(
        (value for key, value in headers.items() if str(key).casefold() == wanted), None
    )
    return str(value) if value is not None else None


def _secondary_reset_delay(response: object) -> float | None:
    """Use exhausted REST quota reset data when GitHub omitted Retry-After."""
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return None
    try:
        remaining = int(_header(headers, "X-RateLimit-Remaining") or "")
        reset = int(_header(headers, "X-RateLimit-Reset") or "")
    except (TypeError, ValueError):
        return None
    if remaining != 0:
        return None
    return max(0.0, reset - datetime.now(UTC).timestamp())


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
        if isinstance(e, gidgethub.BadGraphQLRequest):
            message = str(e).lower()
            if e.status_code == http.HTTPStatus.TOO_MANY_REQUESTS or (
                e.status_code == http.HTTPStatus.FORBIDDEN
                and "secondary rate limit" in message
            ):
                raise GitHubSecondaryRateLimitError(
                    str(e), delay_seconds=_FALLBACK_RATE_LIMIT_DELAY
                ) from e
            if e.status_code == http.HTTPStatus.FORBIDDEN and "rate limit" in message:
                raise GitHubPrimaryRateLimitError(
                    str(e), delay_seconds=_FALLBACK_RATE_LIMIT_DELAY
                ) from e
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
        if partial := _graphql_partial_data(e):
            data, errors = partial
            raise GitHubGraphQLPartialDataError(str(e), data=data, errors=errors) from e
        codes = _graphql_error_codes(e)
        if (
            isinstance(e, gidgethub.BadGraphQLRequest)
            and e.status_code == http.HTTPStatus.NOT_FOUND
        ) or "NOT_FOUND" in codes:
            raise GitHubNotFoundError(str(e)) from e
        if (
            isinstance(e, gidgethub.BadGraphQLRequest)
            and e.status_code == http.HTTPStatus.FORBIDDEN
        ) or "FORBIDDEN" in codes:
            raise GitHubForbiddenError(str(e)) from e
        raise GitHubApiError(str(e)) from e
    except gidgethub.HTTPException as e:
        if e.status_code == http.HTTPStatus.NOT_FOUND:
            raise GitHubNotFoundError(str(e)) from e
        if e.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
            delay = _retry_after(e)
            if delay is None:
                delay = _secondary_reset_delay(e)
            raise GitHubSecondaryRateLimitError(
                str(e),
                delay_seconds=(_FALLBACK_RATE_LIMIT_DELAY if delay is None else delay),
            ) from e
        if e.status_code == http.HTTPStatus.FORBIDDEN:
            if "secondary rate limit" in str(e).lower():
                delay = _retry_after(e)
                if delay is None:
                    delay = _secondary_reset_delay(e)
                raise GitHubSecondaryRateLimitError(
                    str(e),
                    delay_seconds=(
                        _FALLBACK_RATE_LIMIT_DELAY if delay is None else delay
                    ),
                ) from e
            raise GitHubForbiddenError(str(e)) from e
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


def _graphql_partial_data(
    error: gidgethub.GraphQLException,
) -> tuple[Mapping[str, object], tuple[Mapping[str, object], ...]] | None:
    """Return usable GraphQL data and field errors retained by GidgetHub."""
    response = error.response
    if not isinstance(response, Mapping):
        return None
    data = response.get("data")
    errors = response.get("errors")
    if not isinstance(data, Mapping) or not any(
        value is not None for value in data.values()
    ):
        return None
    if not isinstance(errors, list):
        return None
    details = tuple(item for item in errors if isinstance(item, Mapping))
    return data, details


def _is_secondary_graphql_rate_limit(error: gidgethub.GraphQLException) -> bool:
    codes = _graphql_error_codes(error)
    if any("SECONDARY" in code and "RATE" in code for code in codes):
        return True
    return str(error).lower().startswith(_SECONDARY_RATE_LIMIT_MESSAGE.lower())


def _is_primary_graphql_rate_limit(gh, error: gidgethub.GraphQLException) -> bool:
    codes = _graphql_error_codes(error)
    if codes & {"RATE_LIMITED", "RATE_LIMIT_EXCEEDED", "PRIMARY_RATE_LIMITED"}:
        return True
    rate_limit = getattr(gh, "rate_limit", None)
    return getattr(rate_limit, "remaining", None) == 0
