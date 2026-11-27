"""Protocol-based repository-processing architecture.

Defines the RepoProcessor protocol, Monitor protocol, and supporting data types
(ProcessingStatus, FeedbackEvent, RepoResult) for structured repository processing.
Includes concrete implementations: LoggingMonitor and InfoRepoProcessor.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call
from ghbot.log import get_logger

ProcessingStatus = Literal["success", "partial", "failed", "skipped"]
UnavailableReason = Literal["not_found", "forbidden", "disabled", "error"]
_DEPENDABOT_LOGINS = frozenset({"dependabot", "dependabot[bot]"})


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    """A single feedback occurrence during processing."""

    type: str
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class UnavailableMetric:
    """Why a nullable report metric could not be retrieved."""

    reason: UnavailableReason
    message: str | None = None


@dataclass(slots=True)
class RepoResult:
    """Structured result returned by a RepoProcessor after processing completes."""

    owner: str
    repo: str
    status: ProcessingStatus = "success"
    errors: list[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)
    unavailable: dict[str, UnavailableMetric] = field(default_factory=dict)
    reason: str | None = None


def is_dependabot_login(login: object) -> bool:
    """Return whether a GitHub login is one of Dependabot's API identities."""
    return isinstance(login, str) and login in _DEPENDABOT_LOGINS


def record_unavailable(
    result: RepoResult,
    *metrics: str,
    reason: UnavailableReason,
    error: Exception | None = None,
) -> None:
    """Record a concise availability cause for nullable result metrics."""
    message = str(error) if error is not None else None
    unavailable = UnavailableMetric(reason=reason, message=message or None)
    result.unavailable.update(dict.fromkeys(metrics, unavailable))


def unavailable_reason(error: GitHubApiError) -> UnavailableReason:
    if isinstance(error, GitHubNotFoundError):
        return "not_found"
    if isinstance(error, GitHubForbiddenError):
        return "forbidden"
    return "error"


def report_metadata(result: RepoResult) -> dict[str, object]:
    """Return additive report fields shared by every report mode."""
    metadata: dict[str, object] = {}
    if result.status != "success":
        metadata["status"] = result.status
    if result.reason is not None:
        metadata["reason"] = result.reason
    if result.unavailable:
        metadata["unavailable"] = {
            metric: {
                "reason": unavailable.reason,
                **({"message": unavailable.message} if unavailable.message else {}),
            }
            for metric, unavailable in result.unavailable.items()
        }
    return metadata


def display_metric(result: RepoResult, metric: str, value: object) -> object:
    """Render nullable metrics without discarding their availability reason."""
    if value is not None:
        return value
    unavailable = result.unavailable.get(metric)
    return f"N/A ({unavailable.reason})" if unavailable else "N/A"


@runtime_checkable
class Monitor(Protocol):
    """Abstraction for reporting events during processing."""

    async def send_event(self, event: FeedbackEvent) -> None: ...


@runtime_checkable
class RepoProcessor(Protocol):
    """Protocol that all repository processors implement.

    Declares read-only owner and repo attributes and an async run method
    returning a RepoResult.
    """

    @property
    def owner(self) -> str: ...

    @property
    def repo(self) -> str: ...

    async def run(self) -> RepoResult: ...


class GitHubClient(Protocol):
    """GitHub API surface used by repository processors."""

    async def graphql(self, query: str, **_variables: Any) -> Any: ...

    async def getitem(
        self, url: str, *, url_vars: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    def getiter(
        self,
        url: str,
        *,
        url_vars: dict[str, Any] | None = None,
        iterable_key: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]: ...


class InfoRepoProcessor:
    """Concrete RepoProcessor that gathers repository summary statistics."""

    def __init__(
        self,
        owner: str,
        repo: str,
        gh: GitHubClient,
        monitor: Monitor,
        options: dict | None = None,
        *,
        owner_type: str | None = None,
    ) -> None:
        if not owner:
            raise ValueError("owner must be a non-empty string")
        if not repo:
            raise ValueError("repo must be a non-empty string")
        self._owner = owner
        self._repo = repo
        self._gh = gh
        self._monitor = monitor
        del options
        self._owner_type = owner_type

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

    @property
    def owner_type(self) -> str | None:
        return self._owner_type

    async def run(self) -> RepoResult:
        result = RepoResult(owner=self._owner, repo=self._repo)
        await self._monitor.send_event(
            FeedbackEvent("progress", "info", "processing started")
        )

        try:
            await self._fetch_repo_metadata(result)
            await self._fetch_file_count(result)
            await self._fetch_languages(result)
            await self._fetch_contributors(result)
            await self._fetch_latest_release(result)
            await self._fetch_open_pull_requests(result)
            await self._fetch_open_issues(result)
            await self._fetch_security_alerts(result)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except FatalError:
            raise
        except Exception as e:  # noqa: BLE001 - processors report unexpected errors as failed results.
            await self._monitor.send_event(
                FeedbackEvent("error", "error", f"unexpected error: {e}")
            )
            result.status = "failed"
            result.errors.append(str(e))
        else:
            if result.errors:
                result.status = "partial"

        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "processing finished")
        )
        return result

    async def _fetch_repo_metadata(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching repository metadata")
        )
        try:
            async with github_api_call(self._gh):
                data = await self._gh.getitem(
                    "/repos/{owner}/{repo}",
                    url_vars={"owner": self._owner, "repo": self._repo},
                )
            result.results["description"] = data.get("description")
            result.results["updated_at"] = data.get("updated_at")
            result.results["_default_branch"] = data.get("default_branch", "main")
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch repository metadata: {e}"
                )
            )
            result.results["description"] = None
            result.results["updated_at"] = None
            result.results["_default_branch"] = "main"
            result.errors.append(f"repository metadata: {e}")

    async def _fetch_file_count(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching file count")
        )
        try:
            branch = result.results.get("_default_branch", "main")
            async with github_api_call(self._gh):
                data = await self._gh.getitem(
                    "/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                    url_vars={
                        "owner": self._owner,
                        "repo": self._repo,
                        "branch": branch,
                    },
                )
            result.results["file_count"] = sum(
                1 for item in data.get("tree", []) if item.get("type") == "blob"
            )
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch file count: {e}")
            )
            result.results["file_count"] = 0
            result.errors.append(f"file count: {e}")

    async def _fetch_languages(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching languages")
        )
        try:
            async with github_api_call(self._gh):
                data = await self._gh.getitem(
                    "/repos/{owner}/{repo}/languages",
                    url_vars={"owner": self._owner, "repo": self._repo},
                )
            if not data:
                await self._monitor.send_event(
                    FeedbackEvent("fetch", "debug", "no language data available")
                )
            result.results["languages"] = data or {}
        except GitHubNotFoundError:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "debug", "languages endpoint not accessible")
            )
            result.results["languages"] = {}
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch languages: {e}")
            )
            result.results["languages"] = {}
            result.errors.append(f"languages: {e}")

    async def _fetch_contributors(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching contributors")
        )
        try:
            async with github_api_call(self._gh):
                contributors = [
                    item
                    async for item in self._gh.getiter(
                        "/repos/{owner}/{repo}/contributors",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                ]
            result.results["contributors"] = contributors
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch contributors: {e}")
            )
            result.results["contributors"] = []
            result.errors.append(f"contributors: {e}")

    async def _fetch_latest_release(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching latest release")
        )
        try:
            async with github_api_call(self._gh):
                data = await self._gh.getitem(
                    "/repos/{owner}/{repo}/releases/latest",
                    url_vars={"owner": self._owner, "repo": self._repo},
                )
            result.results["latest_release"] = data
        except GitHubNotFoundError:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "debug", "no releases available")
            )
            result.results["latest_release"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch latest release: {e}")
            )
            result.results["latest_release"] = None
            result.errors.append(f"latest release: {e}")

    async def _fetch_open_pull_requests(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching open pull requests")
        )
        try:
            async with github_api_call(self._gh):
                prs = [
                    item
                    async for item in self._gh.getiter(
                        "/repos/{owner}/{repo}/pulls?state=open",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                ]
            result.results["open_pull_requests"] = len(prs)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch open pull requests: {e}"
                )
            )
            result.results["open_pull_requests"] = 0
            result.errors.append(f"open pull requests: {e}")

    async def _fetch_open_issues(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching open issues")
        )
        try:
            async with github_api_call(self._gh):
                issues = [
                    item
                    async for item in self._gh.getiter(
                        "/repos/{owner}/{repo}/issues?state=open",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                ]
            result.results["open_issues"] = len(
                [i for i in issues if i is not None and "pull_request" not in i]
            )
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch open issues: {e}")
            )
            result.results["open_issues"] = 0
            result.errors.append(f"open issues: {e}")

    async def _fetch_security_alerts(self, result: RepoResult) -> None:
        await self._monitor.send_event(
            FeedbackEvent("progress", "debug", "fetching security alerts")
        )
        try:
            async with github_api_call(self._gh):
                alerts = [
                    item
                    async for item in self._gh.getiter(
                        "/repos/{owner}/{repo}/vulnerability-alerts",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                    if item is not None
                ]
            result.results["security_alerts"] = alerts
        except GitHubNotFoundError:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "debug", "security alerts inaccessible")
            )
            result.results["security_alerts"] = []
        except TypeError:
            # 204 No Content — endpoint accessible but no alerts
            result.results["security_alerts"] = []
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch security alerts: {e}")
            )
            result.results["security_alerts"] = []
            result.errors.append(f"security alerts: {e}")


class LoggingMonitor:
    """Concrete Monitor backed by the project's logging infrastructure."""

    def __init__(self, owner: str, repo: str) -> None:
        self._owner = owner
        self._repo = repo
        self._log = get_logger(f"{__name__}.{owner}/{repo}")

    async def send_event(self, event: FeedbackEvent) -> None:
        msg = f"[{event.type}] {self._owner}/{self._repo}: {event.message}"
        level_map = {
            "debug": self._log.debug,
            "info": self._log.info,
            "warning": self._log.warning,
            "error": self._log.error,
        }
        log_fn = level_map.get(event.severity, self._log.warning)
        log_fn(msg)
