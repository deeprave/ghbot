"""Security scanning and reporting mode."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import click

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
from ghbot.processor import (
    FeedbackEvent,
    GitHubClient,
    Monitor,
    RepoResult,
    display_metric,
    is_dependabot_login,
    record_unavailable,
    report_metadata,
    unavailable_reason,
)
from ghbot.report_style import (
    JSONReportStyle,
    PlainReportStyle,
    ReportStyle,
    TableReportStyle,
    output_format,
    write_report,
)
from ghbot.runner import run_mode

log = get_logger(__name__)

_SEVERITY_KEYS = ("critical", "high", "medium", "low", "other")
_RULE_SEVERITY_KEYS = ("error", "warning", "note", "other")


def _severity_counts() -> dict[str, int]:
    return dict.fromkeys(_SEVERITY_KEYS, 0)


def _rule_severity_counts() -> dict[str, int]:
    return dict.fromkeys(_RULE_SEVERITY_KEYS, 0)


def _severity(value: object) -> str:
    return value if isinstance(value, str) and value in _SEVERITY_KEYS[:-1] else "other"


def _dependabot_severity(alert: dict) -> str:
    value = (alert.get("security_advisory") or {}).get("severity")
    return "medium" if value == "moderate" else _severity(value)


def _rule_severity(value: object) -> str:
    return (
        value
        if isinstance(value, str) and value in _RULE_SEVERITY_KEYS[:-1]
        else "other"
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
        del options
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
                breakdown = _severity_counts()
                async for alert in self._gh.getiter(
                    "/repos/{owner}/{repo}/dependabot/alerts?state=open",
                    url_vars={"owner": self._owner, "repo": self._repo},
                ):
                    count += 1
                    breakdown[_dependabot_severity(alert)] += 1
            result.results["dependabot_alerts"] = count
            result.results["dependabot_alerts_by_severity"] = breakdown
        except GitHubNotFoundError as error:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "dependabot alerts not accessible")
            )
            result.results["dependabot_alerts"] = None
            result.results["dependabot_alerts_by_severity"] = None
            record_unavailable(
                result, "dependabot_alerts", reason="not_found", error=error
            )
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            result.results["dependabot_alerts"] = None
            result.results["dependabot_alerts_by_severity"] = None
            await self._record_alert_error(
                result, "dependabot_alerts", "dependabot alerts", error
            )

    async def _fetch_code_scanning_alerts(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching code scanning alerts")
        )
        try:
            async with github_api_call(self._gh):
                count = 0
                security = _severity_counts()
                rule_counts = _rule_severity_counts()
                async for alert in self._gh.getiter(
                    "/repos/{owner}/{repo}/code-scanning/alerts?state=open",
                    url_vars={"owner": self._owner, "repo": self._repo},
                ):
                    count += 1
                    rule = alert.get("rule") or {}
                    value = rule.get("security_severity_level")
                    if value is None:
                        rule_counts[_rule_severity(rule.get("severity"))] += 1
                    else:
                        security[_severity(value)] += 1
            result.results["code_scanning_alerts"] = count
            result.results["code_scanning_alerts_by_security_severity"] = security
            result.results["code_scanning_alerts_by_rule_severity"] = rule_counts
        except GitHubNotFoundError as error:
            if await self._record_feature_not_enabled(
                result, "code_scanning_alerts", error
            ):
                return
            result.results["code_scanning_alerts"] = None
            result.results["code_scanning_alerts_by_security_severity"] = None
            result.results["code_scanning_alerts_by_rule_severity"] = None
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "code scanning alerts not accessible")
            )
            record_unavailable(
                result, "code_scanning_alerts", reason="not_found", error=error
            )
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            result.results["code_scanning_alerts"] = None
            result.results["code_scanning_alerts_by_security_severity"] = None
            result.results["code_scanning_alerts_by_rule_severity"] = None
            await self._record_alert_error(
                result, "code_scanning_alerts", "code scanning alerts", error
            )

    async def _fetch_secret_scanning_alerts(self, result: RepoResult) -> None:
        await self._fetch_alert_count(
            result,
            key="secret_scanning_alerts",
            endpoint="/repos/{owner}/{repo}/secret-scanning/alerts?state=open",
            label="secret scanning alerts",
        )

    async def _fetch_alert_count(
        self,
        result: RepoResult,
        *,
        key: str,
        endpoint: str,
        label: str,
        severity_key: str | None = None,
        severity_for_alert: Callable[[dict], str] | None = None,
    ) -> None:
        await self._defer_event(FeedbackEvent("progress", "debug", f"fetching {label}"))
        try:
            async with github_api_call(self._gh):
                count = 0
                breakdown = _severity_counts() if severity_key else None
                async for alert in self._gh.getiter(
                    endpoint, url_vars={"owner": self._owner, "repo": self._repo}
                ):
                    count += 1
                    if breakdown is not None and severity_for_alert is not None:
                        breakdown[severity_for_alert(alert)] += 1
            result.results[key] = count
            if severity_key:
                result.results[severity_key] = breakdown
        except GitHubNotFoundError as error:
            if await self._record_feature_not_enabled(result, key, error):
                return
            await self._defer_event(
                FeedbackEvent("fetch", "debug", f"{label} not accessible")
            )
            result.results[key] = None
            if severity_key:
                result.results[severity_key] = None
            record_unavailable(result, key, reason="not_found", error=error)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            result.results[key] = None
            if severity_key:
                result.results[severity_key] = None
            await self._record_alert_error(result, key, label, error)

    async def _record_alert_error(
        self, result: RepoResult, key: str, label: str, error: GitHubApiError
    ) -> None:
        if await self._record_feature_not_enabled(result, key, error):
            return
        await self._monitor.send_event(
            FeedbackEvent("fetch", "error", f"failed to fetch {label}: {error}")
        )
        record_unavailable(result, key, reason=unavailable_reason(error), error=error)
        result.errors.append(f"{label}: {error}")

    async def _record_feature_not_enabled(
        self, result: RepoResult, key: str, error: GitHubApiError
    ) -> bool:
        if not (message := _security_feature_not_enabled_message(key, error)):
            return False
        await self._monitor.send_event(FeedbackEvent("fetch", "debug", message))
        record_unavailable(result, key, reason="disabled", error=error)
        return True

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
        except GitHubNotFoundError as error:
            await self._defer_event(
                FeedbackEvent(
                    "fetch", "debug", "dependabot pull requests not accessible"
                )
            )
            result.results["dependabot_open_pull_requests"] = None
            result.results["dependabot_ready_pull_requests"] = None
            record_unavailable(
                result,
                "dependabot_open_pull_requests",
                "dependabot_ready_pull_requests",
                reason="not_found",
                error=error,
            )
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
            record_unavailable(
                result,
                "dependabot_open_pull_requests",
                "dependabot_ready_pull_requests",
                reason=unavailable_reason(error),
                error=error,
            )
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

    def _severity_total(self, key: str) -> dict[str, int] | None:
        values = [result.results.get(key) for result in self.results]
        available = [value for value in values if value is not None]
        if not available:
            return None
        total = _severity_counts()
        for value in available:
            for severity in _SEVERITY_KEYS:
                total[severity] += value[severity]
        return total

    def _rule_severity_total(self, key: str) -> dict[str, int] | None:
        values = [result.results.get(key) for result in self.results]
        available = [value for value in values if value is not None]
        if not available:
            return None
        total = _rule_severity_counts()
        for value in available:
            for severity in _RULE_SEVERITY_KEYS:
                total[severity] += value[severity]
        return total

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
            "dependabot_alerts_by_severity": self._severity_total(
                "dependabot_alerts_by_severity"
            ),
            "code_scanning_alerts": self._total("code_scanning_alerts"),
            "code_scanning_alerts_by_security_severity": self._severity_total(
                "code_scanning_alerts_by_security_severity"
            ),
            "code_scanning_alerts_by_rule_severity": self._rule_severity_total(
                "code_scanning_alerts_by_rule_severity"
            ),
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
                    **report_metadata(result),
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
                    _repository_heading(result),
                    _fmt(
                        "  Dependabot alerts:",
                        display_metric(
                            result,
                            "dependabot_alerts",
                            result.results.get("dependabot_alerts"),
                        ),
                    ),
                    _fmt(
                        "  Dependabot severity:",
                        _result_severity(result, "dependabot_alerts_by_severity"),
                    ),
                    _fmt(
                        "  Code scanning alerts:",
                        display_metric(
                            result,
                            "code_scanning_alerts",
                            result.results.get("code_scanning_alerts"),
                        ),
                    ),
                    _fmt(
                        "  Code scanning severity:",
                        _result_severity(
                            result,
                            "code_scanning_alerts_by_security_severity",
                            metric="code_scanning_alerts",
                        ),
                    ),
                    _fmt(
                        "  Code scanning rule severity:",
                        _result_rule_severity(
                            result, "code_scanning_alerts_by_rule_severity"
                        ),
                    ),
                    _fmt(
                        "  Secret scanning alerts:",
                        display_metric(
                            result,
                            "secret_scanning_alerts",
                            result.results.get("secret_scanning_alerts"),
                        ),
                    ),
                    _fmt(
                        "  Dependabot PRs:",
                        display_metric(
                            result,
                            "dependabot_open_pull_requests",
                            result.results.get("dependabot_open_pull_requests"),
                        ),
                    ),
                    _fmt(
                        "  Dependabot PRs ready:",
                        display_metric(
                            result,
                            "dependabot_ready_pull_requests",
                            result.results.get("dependabot_ready_pull_requests"),
                        ),
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
            (
                result
                for result in self.results
                if self._active(result)
                or result.unavailable
                or result.reason is not None
            ),
            key=lambda result: f"{result.owner}/{result.repo}",
        )

    def _summary_lines(self) -> list[str]:
        summary = self.document()["summary"]
        assert isinstance(summary, dict)
        return [
            _fmt("Repos scanned:", summary["repos_scanned"]),
            _fmt("Repos with issues:", summary["repos_with_issues"]),
            _fmt("Dependabot alerts:", _display(summary["dependabot_alerts"])),
            _fmt(
                "Dependabot severity:",
                _display_severity(summary["dependabot_alerts_by_severity"]),
            ),
            _fmt("Code scanning alerts:", _display(summary["code_scanning_alerts"])),
            _fmt(
                "Code scanning severity:",
                _display_severity(summary["code_scanning_alerts_by_security_severity"]),
            ),
            _fmt(
                "Code scanning rule severity:",
                _display_rule_severity(
                    summary["code_scanning_alerts_by_rule_severity"]
                ),
            ),
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
    combine_key: str = "010"

    @property
    def command(self) -> click.Command:
        return security

    def new_collection(self, options: dict) -> SecurityCollectionReport:
        return SecurityCollectionReport()

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type=None):
        return SecurityRepoProcessor(
            owner, repo, gh, monitor, options=options, owner_type=owner_type
        )


MODE = SecurityMode()


@click.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the final report to a file",
)
@click.pass_context
def security(
    ctx: click.Context,
    format_plain: bool,
    format_table: bool,
    format_json: bool,
    output: Path | None,
) -> None:
    """Scan for open security alerts."""
    selected_format = output_format(
        plain=format_plain, table=format_table, json_format=format_json
    )
    try:
        collection = asyncio.run(
            run_mode(ctx.obj["cfg"], MODE, {"format": selected_format})
        )
    except FatalError as error:
        log.error(error.message)
        sys.exit(error.exit_code)
    write_report(collection.render(selected_format), output)
    if getattr(collection, "exit_code", 0) == 4:
        log.error("rate limited; wrote incomplete report")
        sys.exit(4)
    if getattr(collection, "exit_code", 0) == 8:
        log.error(
            "unavailable explicit repository; wrote report with missing expected data"
        )
        sys.exit(8)


def _fmt(label: str, value: object) -> str:
    return f"{label:<26}{value:>8}"


def _display(value: int | None) -> int | str:
    return "N/A" if value is None else value


def _display_severity(value: dict[str, int] | None) -> str:
    if value is None:
        return "N/A"
    return " ".join(
        f"{severity[0].upper()}{value[severity]}" for severity in _SEVERITY_KEYS
    )


def _result_severity(result: RepoResult, key: str, *, metric: str | None = None) -> str:
    value = result.results.get(key)
    if value is None:
        return str(
            display_metric(result, metric or key.removesuffix("_by_severity"), None)
        )
    return _display_severity(value)


def _display_rule_severity(value: dict[str, int] | None) -> str:
    if value is None:
        return "N/A"
    return " ".join(
        f"{severity[0].upper()}{value[severity]}" for severity in _RULE_SEVERITY_KEYS
    )


def _result_rule_severity(result: RepoResult, key: str) -> str:
    value = result.results.get(key)
    if value is None:
        return str(display_metric(result, "code_scanning_alerts", None))
    return _display_rule_severity(value)


def _repository_heading(result: RepoResult) -> str:
    name = f"{result.owner}/{result.repo}"
    return (
        f"{name} ({result.status}: {result.reason})"
        if result.reason is not None
        else name
    )


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
    user = pull_request.get("user")
    return isinstance(user, dict) and is_dependabot_login(user.get("login"))


def _security_feature_not_enabled_message(
    key: str, error: GitHubApiError
) -> str | None:
    """Translate recognised product-gating responses without hiding their raw detail."""
    if not isinstance(error, (GitHubForbiddenError, GitHubNotFoundError)):
        return None
    error_message = str(error).casefold()
    if key == "code_scanning_alerts" and (
        "advanced security must be enabled" in error_message
        or "code security must be enabled" in error_message
    ):
        return "Code Security is not enabled for this repository."
    if (
        key == "secret_scanning_alerts"
        and "secret scanning is disabled" in error_message
    ):
        return "Secret scanning is not enabled for this repository."
    if key == "dependabot_alerts" and "dependabot alerts are disabled" in error_message:
        return "Dependabot alerts are not enabled for this repository."
    return None


def _check_run_is_ready(check_run: dict) -> bool:
    return check_run.get("status") == "completed" and check_run.get("conclusion") in {
        "success",
        "neutral",
        "skipped",
    }


def _table_header() -> str:
    return (
        f"|{'Repository':<48}|{' Dependabot ':>16}|{' Scanning ':>16}"
        f"|{' Dep Sev ':>16}|{' Scan Sec ':>16}|{' Scan Rule ':>16}|{' Secrets ':>16}|{' Dep PRs ':>16}|{' Ready ':>16}|"
    )


def _table_separator() -> str:
    return (
        "|"
        + "|".join("-" * width for width in (48, 16, 16, 16, 16, 16, 16, 16, 16))
        + "|"
    )


def _table_row(result: RepoResult) -> str:
    values = (
        _table_repository(result),
        display_metric(
            result, "dependabot_alerts", result.results.get("dependabot_alerts")
        ),
        display_metric(
            result, "code_scanning_alerts", result.results.get("code_scanning_alerts")
        ),
        _result_severity(result, "dependabot_alerts_by_severity"),
        _result_severity(
            result,
            "code_scanning_alerts_by_security_severity",
            metric="code_scanning_alerts",
        ),
        _result_rule_severity(result, "code_scanning_alerts_by_rule_severity"),
        display_metric(
            result,
            "secret_scanning_alerts",
            result.results.get("secret_scanning_alerts"),
        ),
        display_metric(
            result,
            "dependabot_open_pull_requests",
            result.results.get("dependabot_open_pull_requests"),
        ),
        display_metric(
            result,
            "dependabot_ready_pull_requests",
            result.results.get("dependabot_ready_pull_requests"),
        ),
    )
    return (
        f"|{values[0]:<48}|{values[1]:>16}|{values[2]:>16}|{values[3]:>16}|{values[4]:>16}"
        f"|{values[5]:>16}|{values[6]:>16}|{values[7]:>16}|{values[8]:>16}|"
    )


def _table_repository(result: RepoResult) -> str:
    name = f"{result.owner}/{result.repo}"
    return f"{name} ({result.status}: {result.reason})" if result.reason else name
