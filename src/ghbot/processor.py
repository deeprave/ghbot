"""Protocol-based repository-processing architecture.

Defines the RepoProcessor protocol, Monitor protocol, and supporting data types
(ProcessingStatus, FeedbackEvent, RepoResult) for structured repository processing.
Includes concrete implementations: LoggingMonitor and InfoRepoProcessor.
"""

from dataclasses import dataclass, field
from collections.abc import AsyncIterator
from typing import Any, Literal, Protocol, runtime_checkable

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call
from ghbot.log import get_logger

ProcessingStatus = Literal["success", "partial", "failed"]
_DEPENDABOT_LOGIN = "dependabot[bot]"
_NON_BLOCKING_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    """A single feedback occurrence during processing."""

    type: str
    severity: str
    message: str


@dataclass(slots=True)
class RepoResult:
    """Structured result returned by a RepoProcessor after processing completes."""

    owner: str
    repo: str
    status: ProcessingStatus = "success"
    errors: list[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)


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

    async def getitem(
        self, url: str, *, url_vars: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    def getiter(
        self, url: str, *, url_vars: dict[str, Any] | None = None
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
    ) -> None:
        if not owner:
            raise ValueError("owner must be a non-empty string")
        if not repo:
            raise ValueError("repo must be a non-empty string")
        self._owner = owner
        self._repo = repo
        self._gh = gh
        self._monitor = monitor
        self._options = dict(options or {})

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

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
        except Exception as e:
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


class SecurityRepoProcessor:
    """Concrete RepoProcessor that collects open security alerts per repository."""

    def __init__(
        self,
        owner: str,
        repo: str,
        gh: GitHubClient,
        monitor: Monitor,
        options: dict | None = None,
    ) -> None:
        if not owner:
            raise ValueError("owner must be a non-empty string")
        if not repo:
            raise ValueError("repo must be a non-empty string")
        self._owner = owner
        self._repo = repo
        self._gh = gh
        self._monitor = monitor
        self._options = dict(options or {})
        self._deferred_events: list[FeedbackEvent] = []

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

    async def run(self) -> RepoResult:
        result = RepoResult(owner=self._owner, repo=self._repo)
        self._deferred_events = []
        try:
            await self._fetch_dependabot_alerts(result)
            await self._fetch_code_scanning_alerts(result)
            await self._fetch_secret_scanning_alerts(result)
            await self._fetch_dependabot_pull_requests(result)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except FatalError:
            raise
        except Exception as e:
            await self._monitor.send_event(
                FeedbackEvent("error", "error", f"unexpected error: {e}")
            )
            result.status = "failed"
            result.errors.append(str(e))
        else:
            if result.errors:
                result.status = "partial"
        await self._defer_event(
            FeedbackEvent("progress", "debug", "processing finished")
        )
        if activity_message := _security_activity_message(result):
            await self._monitor.send_event(
                FeedbackEvent("progress", "info", activity_message)
            )
            for event in self._deferred_events:
                await self._monitor.send_event(event)
        return result

    async def _defer_event(self, event: FeedbackEvent) -> None:
        self._deferred_events.append(event)

    async def _fetch_dependabot_alerts(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching dependabot alerts")
        )
        try:
            async with github_api_call(self._gh):
                count = 0
                async for _ in self._gh.getiter(
                    "/repos/{owner}/{repo}/dependabot/alerts?state=open",
                    url_vars={"owner": self._owner, "repo": self._repo},
                ):
                    count += 1
            result.results["dependabot_alerts"] = count
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "dependabot alerts not accessible")
            )
            result.results["dependabot_alerts"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch dependabot alerts: {e}"
                )
            )
            result.results["dependabot_alerts"] = None
            result.errors.append(f"dependabot alerts: {e}")

    async def _fetch_code_scanning_alerts(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching code scanning alerts")
        )
        try:
            async with github_api_call(self._gh):
                count = 0
                async for _ in self._gh.getiter(
                    "/repos/{owner}/{repo}/code-scanning/alerts?state=open",
                    url_vars={"owner": self._owner, "repo": self._repo},
                ):
                    count += 1
            result.results["code_scanning_alerts"] = count
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "code scanning alerts not accessible")
            )
            result.results["code_scanning_alerts"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch code scanning alerts: {e}"
                )
            )
            result.results["code_scanning_alerts"] = None
            result.errors.append(f"code scanning alerts: {e}")

    async def _fetch_secret_scanning_alerts(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching secret scanning alerts")
        )
        try:
            async with github_api_call(self._gh):
                count = 0
                async for _ in self._gh.getiter(
                    "/repos/{owner}/{repo}/secret-scanning/alerts?state=open",
                    url_vars={"owner": self._owner, "repo": self._repo},
                ):
                    count += 1
            result.results["secret_scanning_alerts"] = count
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "secret scanning alerts not accessible")
            )
            result.results["secret_scanning_alerts"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch secret scanning alerts: {e}"
                )
            )
            result.results["secret_scanning_alerts"] = None
            result.errors.append(f"secret scanning alerts: {e}")

    async def _fetch_dependabot_pull_requests(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching dependabot pull requests")
        )
        try:
            async with github_api_call(self._gh):
                pull_requests = [
                    pr
                    async for pr in self._gh.getiter(
                        "/repos/{owner}/{repo}/pulls?state=open",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                    if _is_dependabot_pull_request(pr)
                ]
            result.results["dependabot_open_pull_requests"] = len(pull_requests)
            result.results["dependabot_ready_pull_requests"] = sum(
                1
                for ready in [
                    await self._dependabot_pull_request_is_ready(pr, result)
                    for pr in pull_requests
                ]
                if ready
            )
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent(
                    "fetch", "debug", "dependabot pull requests not accessible"
                )
            )
            result.results["dependabot_open_pull_requests"] = None
            result.results["dependabot_ready_pull_requests"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch",
                    "error",
                    f"failed to fetch dependabot pull requests: {e}",
                )
            )
            result.results["dependabot_open_pull_requests"] = None
            result.results["dependabot_ready_pull_requests"] = None
            result.errors.append(f"dependabot pull requests: {e}")

    async def _dependabot_pull_request_is_ready(
        self, pull_request: dict[str, Any], result: RepoResult
    ) -> bool:
        if pull_request.get("draft") or pull_request.get("mergeable") is False:
            return False
        if not (sha := (pull_request.get("head") or {}).get("sha")):
            result.errors.append("dependabot pull request readiness: missing head sha")
            return False
        try:
            return await self._commit_status_is_ready(
                sha
            ) and await self._check_runs_are_ready(sha)
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent(
                    "fetch",
                    "debug",
                    "dependabot pull request readiness not accessible",
                )
            )
            return False
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            result.errors.append(f"dependabot pull request readiness: {e}")
            return False

    async def _commit_status_is_ready(self, sha: str) -> bool:
        async with github_api_call(self._gh):
            data = await self._gh.getitem(
                "/repos/{owner}/{repo}/commits/{ref}/status",
                url_vars={"owner": self._owner, "repo": self._repo, "ref": sha},
            )
        return data.get("state") == "success"

    async def _check_runs_are_ready(self, sha: str) -> bool:
        async with github_api_call(self._gh):
            data = await self._gh.getitem(
                "/repos/{owner}/{repo}/commits/{ref}/check-runs",
                url_vars={"owner": self._owner, "repo": self._repo, "ref": sha},
            )
        return all(_check_run_is_ready(run) for run in data.get("check_runs", []))


def _security_activity_message(result: RepoResult) -> str | None:
    alert_count = _security_alert_count(result)
    dependabot_pr_count = _dependabot_pull_request_count(result)
    parts = []
    if alert_count:
        parts.append(f"alerts {alert_count}")
    if dependabot_pr_count:
        parts.append(f"dependabot PRs {dependabot_pr_count}")
    return f"found {', '.join(parts)}" if parts else None


def _security_alert_count(result: RepoResult) -> int:
    return sum(
        count
        for count in (
            result.results.get("dependabot_alerts"),
            result.results.get("code_scanning_alerts"),
            result.results.get("secret_scanning_alerts"),
        )
        if count is not None
    )


def _dependabot_pull_request_count(result: RepoResult) -> int:
    return sum(
        count
        for count in (result.results.get("dependabot_open_pull_requests"),)
        if count is not None
    )


def _is_dependabot_pull_request(pull_request: dict[str, Any]) -> bool:
    return (pull_request.get("user") or {}).get("login") == _DEPENDABOT_LOGIN


def _check_run_is_ready(check_run: dict[str, Any]) -> bool:
    return (
        check_run.get("status") == "completed"
        and check_run.get("conclusion") in _NON_BLOCKING_CHECK_CONCLUSIONS
    )


class IssuesRepoProcessor:
    """Concrete RepoProcessor that collects open issues per repository."""

    def __init__(
        self,
        owner: str,
        repo: str,
        gh: GitHubClient,
        monitor: Monitor,
        options: dict | None = None,
    ) -> None:
        if not owner:
            raise ValueError("owner must be a non-empty string")
        if not repo:
            raise ValueError("repo must be a non-empty string")
        self._owner = owner
        self._repo = repo
        self._gh = gh
        self._monitor = monitor
        self._options = dict(options or {})
        self._deferred_events: list[FeedbackEvent] = []

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

    async def run(self) -> RepoResult:
        result = RepoResult(owner=self._owner, repo=self._repo)
        self._deferred_events = []
        try:
            await self._fetch_open_items(result)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except FatalError:
            raise
        except Exception as e:
            await self._monitor.send_event(
                FeedbackEvent("error", "error", f"unexpected error: {e}")
            )
            result.status = "failed"
            result.errors.append(str(e))
        else:
            if result.errors:
                result.status = "partial"
        await self._defer_event(
            FeedbackEvent("progress", "debug", "processing finished")
        )
        if activity_message := _issues_activity_message(result):
            await self._monitor.send_event(
                FeedbackEvent("progress", "info", activity_message)
            )
            for event in self._deferred_events:
                await self._monitor.send_event(event)
        return result

    async def _defer_event(self, event: FeedbackEvent) -> None:
        self._deferred_events.append(event)

    async def _fetch_open_items(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching open items")
        )
        try:
            async with github_api_call(self._gh):
                items = [
                    _item_record(item)
                    async for item in self._gh.getiter(
                        "/repos/{owner}/{repo}/issues?state=open",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                ]
            result.results["open_item_count"] = len(items)
            result.results["open_items"] = items
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "open items not accessible")
            )
            result.results["open_item_count"] = None
            result.results["open_items"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch open items: {e}")
            )
            result.results["open_item_count"] = None
            result.results["open_items"] = None
            result.errors.append(f"open items: {e}")


def _item_type(item: dict[str, Any]) -> str:
    return "pr" if "pull_request" in item else "issue"


def _item_labels(item: dict[str, Any]) -> list[str]:
    return [
        label["name"]
        for label in (item.get("labels") or [])
        if isinstance(label, dict) and label.get("name")
    ]


def _item_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item["number"],
        "title": item.get("title") or "",
        "type": _item_type(item),
        "labels": _item_labels(item),
    }


def _issues_activity_message(result: RepoResult) -> str | None:
    count = result.results.get("open_item_count")
    return f"found {count} open items" if count else None
