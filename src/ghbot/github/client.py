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
    except gidgethub.HTTPException as e:
        if e.status_code == http.HTTPStatus.NOT_FOUND:
            raise GitHubNotFoundError(str(e)) from e
        if e.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
            raise GitHubSecondaryRateLimitError(str(e)) from e
        if e.status_code == http.HTTPStatus.FORBIDDEN:
            raise GitHubNotFoundError(str(e)) from e  # access denied — skip
        raise GitHubApiError(str(e)) from e
