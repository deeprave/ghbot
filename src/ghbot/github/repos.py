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
type RepositoryReference = tuple[str, str]


@dataclass(frozen=True, slots=True)
class DiscoveredRepository:
    """A repository and the owner classification used to discover it."""

    owner: str
    metadata: dict
    owner_type: OwnerType

    @property
    def name(self) -> str:
        return self.metadata["name"]


def _owner_type(metadata: dict, owner: str) -> OwnerType:
    account_type = metadata.get("type")
    if account_type in {"User", "Organization"}:
        return account_type
    log.warning("Unknown owner type for %s", owner)
    return None


async def list_repos(
    owner: str, gh: gh_httpx.GitHubAPI
) -> AsyncGenerator[DiscoveredRepository]:
    for attempt in range(2):
        try:
            async with github_api_call(gh):
                account = await gh.getitem("/users/{owner}", url_vars={"owner": owner})
            owner_type = _owner_type(account, owner)
            list_path = (
                "/orgs/{owner}/repos"
                if owner_type == "Organization"
                else "/users/{owner}/repos"
            )
            async with github_api_call(gh):
                repositories = [
                    DiscoveredRepository(owner, repo, owner_type)
                    async for repo in gh.getiter(
                        list_path, url_vars={"owner": owner, "type": "all"}
                    )
                ]
            for repository in repositories:
                yield repository
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


async def _explicit_repository(
    owner: str, repo: str, gh: gh_httpx.GitHubAPI
) -> DiscoveredRepository | None:
    for attempt in range(2):
        try:
            async with github_api_call(gh):
                metadata = await gh.getitem(
                    "/repos/{owner}/{repo}", url_vars={"owner": owner, "repo": repo}
                )
            owner_metadata = metadata.get("owner")
            owner_type = _owner_type(
                owner_metadata if isinstance(owner_metadata, dict) else {}, owner
            )
            return DiscoveredRepository(owner, metadata, owner_type)
        except GitHubNotFoundError:
            log.warning(
                "Repository not found or inaccessible, skipping: %s/%s", owner, repo
            )
            return None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            if attempt == 1:
                log.error("GitHub API error for %s/%s, skipping: %s", owner, repo, e)
                return None
    return None


async def scan_repositories(
    owners: Sequence[str],
    gh: gh_httpx.GitHubAPI,
    *,
    explicit_repositories: Sequence[RepositoryReference] | None = None,
) -> AsyncGenerator[DiscoveredRepository]:
    if explicit_repositories is not None:
        for owner, repo in explicit_repositories:
            discovered = await _explicit_repository(owner, repo, gh)
            if discovered is None:
                skipped = getattr(gh, "_ghbot_skipped_explicit_ids", None)
                if isinstance(skipped, set):
                    skipped.add(f"{owner}/{repo}".casefold())
                continue
            if discovered.metadata.get("archived", False):
                log.debug("Archived repository, skipping: %s/%s", owner, repo)
                skipped = getattr(gh, "_ghbot_skipped_explicit_ids", None)
                if isinstance(skipped, set):
                    skipped.add(f"{owner}/{repo}".casefold())
                continue
            yield discovered
        return

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
