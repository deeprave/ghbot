from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from typing import Literal

import gidgethub.httpx as gh_httpx

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call
from ghbot.log import get_logger

log = get_logger(__name__)


OwnerType = Literal["User", "Organization"] | None


@dataclass(frozen=True, slots=True)
class DiscoveredRepository:
    """A repository and the owner classification used to discover it."""

    owner: str
    metadata: dict
    owner_type: OwnerType

    @property
    def name(self) -> str:
        return self.metadata["name"]


async def list_repos(
    owner: str, gh: gh_httpx.GitHubAPI
) -> AsyncGenerator[DiscoveredRepository]:
    for attempt in range(2):
        try:
            async with github_api_call(gh):
                account = await gh.getitem("/users/{owner}", url_vars={"owner": owner})
            account_type = account.get("type")
            if account_type in {"User", "Organization"}:
                owner_type: OwnerType = account_type
            else:
                owner_type = None
                log.warning("Unknown owner type for %s; using user endpoint", owner)
            list_path = (
                "/orgs/{owner}/repos"
                if owner_type == "Organization"
                else "/users/{owner}/repos"
            )
            async with github_api_call(gh):
                async for repo in gh.getiter(
                    list_path, url_vars={"owner": owner, "type": "all"}
                ):
                    yield DiscoveredRepository(owner, repo, owner_type)
            return
        except GitHubNotFoundError:
            log.warning("Owner not found, skipping: %s", owner)
            return
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            if attempt == 1:
                log.error("GitHub API error for %s, skipping: %s", owner, e)
                return


async def scan_repositories(
    owners: Sequence[str], gh: gh_httpx.GitHubAPI
) -> AsyncGenerator[DiscoveredRepository]:
    if not owners:
        log.warning("No owners specified")
        return
    for owner in owners:
        async for discovered in list_repos(owner, gh):
            if discovered.metadata.get("archived", False):
                log.debug(
                    "Archived repository, skipping: %s/%s", owner, discovered.name
                )
                continue
            yield discovered
