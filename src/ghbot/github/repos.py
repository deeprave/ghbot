from typing import AsyncGenerator, Sequence

import gidgethub.httpx as gh_httpx

from ghbot.errors import GitHubApiError, GitHubNotFoundError
from ghbot.github.client import github_api_call
from ghbot.log import get_logger

log = get_logger(__name__)


async def list_repos(owner: str, gh: gh_httpx.GitHubAPI) -> AsyncGenerator[dict, None]:
    for attempt in range(2):
        try:
            async with github_api_call(gh):
                async for repo in gh.getiter(
                    f"/users/{owner}/repos", url_vars={"type": "all"}
                ):
                    yield repo
            return
        except GitHubNotFoundError:
            log.warning("Owner not found, skipping: %s", owner)
            return
        except GitHubApiError as e:
            if attempt == 1:
                log.error("GitHub API error for %s, skipping: %s", owner, e)
                return


async def scan_repositories(
    owners: Sequence[str], gh: gh_httpx.GitHubAPI
) -> AsyncGenerator[tuple[str, dict], None]:
    if not owners:
        log.warning("No owners specified")
        return
    for owner in owners:
        async for repo in list_repos(owner, gh):
            yield owner, repo
