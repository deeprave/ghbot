import asyncio
import http
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

_RETRY_DELAY = 1.0
_RETRYABLE = (gidgethub.GitHubBroken, httpx.TransportError)


@asynccontextmanager
async def github_api_call(gh):
    log = get_logger("ghbot.requests")
    log.debug("github api call starting")
    try:
        yield
        log.debug("github api call completed")
    except _RETRYABLE as e:
        await asyncio.sleep(_RETRY_DELAY)
        raise GitHubApiError(str(e)) from e
    except gidgethub.RateLimitExceeded as e:
        raise GitHubPrimaryRateLimitError(str(e)) from e
    except gidgethub.GraphQLException as e:
        if _is_secondary_graphql_rate_limit(e):
            raise GitHubSecondaryRateLimitError(str(e)) from e
        if _is_primary_graphql_rate_limit(gh, e):
            raise GitHubPrimaryRateLimitError(str(e)) from e
        raise GitHubApiError(str(e)) from e
    except gidgethub.HTTPException as e:
        if e.status_code == http.HTTPStatus.NOT_FOUND:
            raise GitHubNotFoundError(str(e)) from e
        if e.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
            raise GitHubSecondaryRateLimitError(str(e)) from e
        if e.status_code == http.HTTPStatus.FORBIDDEN:
            if "secondary rate limit" in str(e).lower():
                raise GitHubSecondaryRateLimitError(str(e)) from e
            raise GitHubNotFoundError(str(e)) from e  # access denied — skip
        raise GitHubApiError(str(e)) from e


def _graphql_error_codes(error: gidgethub.GraphQLException) -> set[str]:
    response = error.response
    if not isinstance(response, dict):
        return set()
    errors = response.get("errors")
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return set()
    details = errors[0]
    extensions = details.get("extensions")
    values = [details.get("type")]
    if isinstance(extensions, dict):
        values.extend((extensions.get("code"), extensions.get("type")))
    return {value.upper() for value in values if isinstance(value, str)}


def _is_secondary_graphql_rate_limit(error: gidgethub.GraphQLException) -> bool:
    codes = _graphql_error_codes(error)
    if any("SECONDARY" in code and "RATE" in code for code in codes):
        return True
    return "secondary rate limit" in str(error).lower()


def _is_primary_graphql_rate_limit(gh, error: gidgethub.GraphQLException) -> bool:
    codes = _graphql_error_codes(error)
    if codes & {"RATE_LIMITED", "RATE_LIMIT_EXCEEDED", "PRIMARY_RATE_LIMITED"}:
        return True
    rate_limit = getattr(gh, "rate_limit", None)
    return getattr(rate_limit, "remaining", None) == 0
