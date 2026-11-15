"""Security scanning and reporting mode."""

from __future__ import annotations

from dataclasses import dataclass, field

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call
from ghbot.processor import FeedbackEvent, GitHubClient, Monitor, RepoResult
from ghbot.report_style import (
    JSONReportStyle,
    PlainReportStyle,
    ReportStyle,
    TableReportStyle,
)


class SecurityRepoProcessor:
    """Security scanner owned by the security mode module.

    The security mode's repository scanner.
    """

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
        self._options = dict(options or {})
        self._owner_type = owner_type
        self._deferred_events: list[FeedbackEvent] = []

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
        except Exception as error:  # noqa: BLE001 - processor returns a failed result.
            await self._monitor.send_event(
                FeedbackEvent("error", "error", f"unexpected error: {error}")
            )
            result.status = "failed"
            result.errors.append(str(error))
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
        except GitHubApiError as error:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch dependabot alerts: {error}"
                )
            )
            result.results["dependabot_alerts"] = None
            result.errors.append(f"dependabot alerts: {error}")

    async def _fetch_code_scanning_alerts(self, result: RepoResult) -> None:
        await self._fetch_alert_count(
            result,
            key="code_scanning_alerts",
            endpoint="/repos/{owner}/{repo}/code-scanning/alerts?state=open",
            label="code scanning alerts",
        )

    async def _fetch_secret_scanning_alerts(self, result: RepoResult) -> None:
        await self._fetch_alert_count(
            result,
            key="secret_scanning_alerts",
            endpoint="/repos/{owner}/{repo}/secret-scanning/alerts?state=open",
            label="secret scanning alerts",
        )

    async def _fetch_alert_count(
        self, result: RepoResult, *, key: str, endpoint: str, label: str
    ) -> None:
        await self._defer_event(FeedbackEvent("progress", "debug", f"fetching {label}"))
        try:
            async with github_api_call(self._gh):
                count = 0
                async for _ in self._gh.getiter(
                    endpoint, url_vars={"owner": self._owner, "repo": self._repo}
                ):
                    count += 1
            result.results[key] = count
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", f"{label} not accessible")
            )
            result.results[key] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch {label}: {error}")
            )
            result.results[key] = None
            result.errors.append(f"{label}: {error}")

    async def _fetch_dependabot_pull_requests(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching dependabot pull requests")
        )
        try:
            async with github_api_call(self._gh):
                pull_requests = [
                    pull_request
                    async for pull_request in self._gh.getiter(
                        "/repos/{owner}/{repo}/pulls?state=open",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                    if _is_dependabot_pull_request(pull_request)
                ]
            result.results["dependabot_open_pull_requests"] = len(pull_requests)
            result.results["dependabot_ready_pull_requests"] = sum(
                1
                for ready in [
                    await self._dependabot_pull_request_is_ready(pull_request, result)
                    for pull_request in pull_requests
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
        except GitHubApiError as error:
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch",
                    "error",
                    f"failed to fetch dependabot pull requests: {error}",
                )
            )
            result.results["dependabot_open_pull_requests"] = None
            result.results["dependabot_ready_pull_requests"] = None
            result.errors.append(f"dependabot pull requests: {error}")

    async def _dependabot_pull_request_is_ready(
        self, pull_request: dict, result: RepoResult
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
                    "fetch", "debug", "dependabot pull request readiness not accessible"
                )
            )
            return False
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            result.errors.append(f"dependabot pull request readiness: {error}")
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


@dataclass(slots=True)
class SecurityCollectionReport:
    results: list[RepoResult] = field(default_factory=list)

    def add(self, result: RepoResult) -> None:
        self.results.append(result)

    def _total(self, key: str) -> int | None:
        values = [result.results.get(key) for result in self.results]
        if all(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)

    def _active(self, result: RepoResult) -> bool:
        return any(
            result.results.get(key) not in (None, 0)
            for key in (
                "dependabot_alerts",
                "code_scanning_alerts",
                "secret_scanning_alerts",
                "dependabot_open_pull_requests",
                "dependabot_ready_pull_requests",
            )
        )

    def document(self) -> dict[str, object]:
        summary = {
            "repos_scanned": len(self.results),
            "repos_with_issues": sum(self._active(result) for result in self.results),
            "dependabot_alerts": self._total("dependabot_alerts"),
            "code_scanning_alerts": self._total("code_scanning_alerts"),
            "secret_scanning_alerts": self._total("secret_scanning_alerts"),
            "dependabot_open_pull_requests": self._total(
                "dependabot_open_pull_requests"
            ),
            "dependabot_ready_pull_requests": self._total(
                "dependabot_ready_pull_requests"
            ),
        }
        return {
            "summary": summary,
            "repositories": [
                dict(
                    result.results,
                    owner=result.owner,
                    repo=result.repo,
                    repository=f"{result.owner}/{result.repo}",
                )
                for result in self.results
            ],
        }

    def render(self, style: ReportStyle | str) -> str:
        if isinstance(style, str):
            style = ReportStyle.from_format(style)
        if isinstance(style, JSONReportStyle):
            return style.render_document(self.document())
        lines = self._summary_lines()
        active = self._active_results()
        for result in active:
            lines.extend(
                [
                    "",
                    f"{result.owner}/{result.repo}",
                    _fmt(
                        "  Dependabot alerts:",
                        _display(result.results.get("dependabot_alerts")),
                    ),
                    _fmt(
                        "  Code scanning alerts:",
                        _display(result.results.get("code_scanning_alerts")),
                    ),
                    _fmt(
                        "  Secret scanning alerts:",
                        _display(result.results.get("secret_scanning_alerts")),
                    ),
                    _fmt(
                        "  Dependabot PRs:",
                        _display(result.results.get("dependabot_open_pull_requests")),
                    ),
                    _fmt(
                        "  Dependabot PRs ready:",
                        _display(result.results.get("dependabot_ready_pull_requests")),
                    ),
                ]
            )
        if isinstance(style, PlainReportStyle):
            return style.render_lines(lines)
        assert isinstance(style, TableReportStyle)
        lines = self._summary_lines()
        if active:
            lines.extend(["", _table_header(), _table_separator()])
            lines.extend(_table_row(result) for result in active)
        return style.render_lines(lines)

    def _active_results(self) -> list[RepoResult]:
        return sorted(
            (result for result in self.results if self._active(result)),
            key=lambda result: f"{result.owner}/{result.repo}",
        )

    def _summary_lines(self) -> list[str]:
        summary = self.document()["summary"]
        assert isinstance(summary, dict)
        return [
            _fmt("Repos scanned:", summary["repos_scanned"]),
            _fmt("Repos with issues:", summary["repos_with_issues"]),
            _fmt("Dependabot alerts:", _display(summary["dependabot_alerts"])),
            _fmt("Code scanning alerts:", _display(summary["code_scanning_alerts"])),
            _fmt(
                "Secret scanning alerts:", _display(summary["secret_scanning_alerts"])
            ),
            _fmt("Dependabot PRs:", _display(summary["dependabot_open_pull_requests"])),
            _fmt(
                "Dependabot PRs ready:",
                _display(summary["dependabot_ready_pull_requests"]),
            ),
        ]


@dataclass(frozen=True, slots=True)
class SecurityMode:
    name: str = "security"
    processor_type: type = SecurityRepoProcessor

    def new_collection(self, options: dict) -> SecurityCollectionReport:
        return SecurityCollectionReport()

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type=None):
        return SecurityRepoProcessor(
            owner, repo, gh, monitor, options=options, owner_type=owner_type
        )


MODE = SecurityMode()


def _fmt(label: str, value: int | str) -> str:
    return f"{label:<26}{value:>8}"


def _display(value: int | None) -> int | str:
    return "N/A" if value is None else value


def _security_activity_message(result: RepoResult) -> str | None:
    alert_count = sum(
        count
        for count in (
            result.results.get("dependabot_alerts"),
            result.results.get("code_scanning_alerts"),
            result.results.get("secret_scanning_alerts"),
        )
        if count is not None
    )
    pull_request_count = sum(
        count
        for count in (result.results.get("dependabot_open_pull_requests"),)
        if count is not None
    )
    parts = []
    if alert_count:
        parts.append(f"alerts {alert_count}")
    if pull_request_count:
        parts.append(f"dependabot PRs {pull_request_count}")
    return f"found {', '.join(parts)}" if parts else None


def _is_dependabot_pull_request(pull_request: dict) -> bool:
    return (pull_request.get("user") or {}).get("login") == "dependabot[bot]"


def _check_run_is_ready(check_run: dict) -> bool:
    return check_run.get("status") == "completed" and check_run.get("conclusion") in {
        "success",
        "neutral",
        "skipped",
    }


def _table_header() -> str:
    return (
        f"|{'Repository':<38}|{' Dependabot ':>12}|{' Scanning ':>10}"
        f"|{' Secrets ':>9}|{' Dep PRs ':>9}|{' Ready ':>7}|"
    )


def _table_separator() -> str:
    return "|" + "|".join("-" * width for width in (38, 12, 10, 9, 9, 7)) + "|"


def _table_row(result: RepoResult) -> str:
    values = (
        f"{result.owner}/{result.repo}",
        _display(result.results.get("dependabot_alerts")),
        _display(result.results.get("code_scanning_alerts")),
        _display(result.results.get("secret_scanning_alerts")),
        _display(result.results.get("dependabot_open_pull_requests")),
        _display(result.results.get("dependabot_ready_pull_requests")),
    )
    return (
        f"|{values[0]:<38}|{values[1]:>12}|{values[2]:>10}|{values[3]:>9}"
        f"|{values[4]:>9}|{values[5]:>7}|"
    )
