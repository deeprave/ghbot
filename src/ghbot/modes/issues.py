"""Issue and pull-request scanning and reporting mode."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call
from ghbot.log import get_logger
from ghbot.processor import FeedbackEvent, GitHubClient, Monitor, RepoResult
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

_OPEN_PULL_REQUESTS_QUERY = """
query OpenPullRequests($owner: String!, $repo: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, states: OPEN, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { number author { login } mergeStateStatus createdAt url isDraft }
    }
  }
}
"""
_PULL_REQUEST_COUNT_METRIC_KEYS = (
    "dependabot_open_pull_requests",
    "dependabot_merge_ready_pull_requests",
    "other_open_pull_requests",
    "other_merge_ready_pull_requests",
)
_PULL_REQUEST_AGE_METRIC_KEYS = (
    "oldest_dependabot_pull_request_created_at",
    "oldest_other_pull_request_created_at",
)
_PULL_REQUEST_METRIC_KEYS = (
    *_PULL_REQUEST_COUNT_METRIC_KEYS,
    *_PULL_REQUEST_AGE_METRIC_KEYS,
)
_DEPENDABOT_PULL_REQUESTS_KEY = "dependabot_pull_requests"


class IssuesRepoProcessor:
    """Collect open issues and pull requests for one repository."""

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
            await self._fetch_open_items(result)
            await self._fetch_open_pull_request_metrics(result)
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
        except GitHubApiError as error:
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch open items: {error}")
            )
            result.results["open_item_count"] = None
            result.results["open_items"] = None
            result.errors.append(f"open items: {error}")

    async def _fetch_open_pull_request_metrics(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching open pull requests")
        )
        count_metrics: dict[str, int] = {
            key: 0 for key in _PULL_REQUEST_COUNT_METRIC_KEYS
        }
        oldest: dict[str, tuple[datetime, str]] = {}
        dependabot_pull_requests: list[dict[str, object]] = []
        after = None
        continuation_cursors: set[str] = set()
        try:
            while True:
                async with github_api_call(self._gh):
                    data = await self._gh.graphql(
                        _OPEN_PULL_REQUESTS_QUERY,
                        owner=self._owner,
                        repo=self._repo,
                        after=after,
                    )
                connection = _pull_request_connection(data)
                for pull_request in connection["nodes"]:
                    number, created_at, url, draft, created = _pull_request_data(
                        pull_request
                    )
                    author = pull_request.get("author")
                    if author is None:
                        author = {}
                    if not isinstance(author, dict):
                        raise TypeError("pull-request author is invalid")
                    prefix = (
                        "dependabot"
                        if author.get("login") == "dependabot[bot]"
                        else "other"
                    )
                    count_metrics[f"{prefix}_open_pull_requests"] += 1
                    if pull_request.get("mergeStateStatus") == "CLEAN":
                        count_metrics[f"{prefix}_merge_ready_pull_requests"] += 1
                    if (previous := oldest.get(prefix)) is None or created < previous[
                        0
                    ]:
                        oldest[prefix] = (created, created_at)
                    if prefix == "dependabot":
                        dependabot_pull_requests.append(
                            {
                                "number": number,
                                "url": url,
                                "created_at": created_at,
                                "draft": draft,
                                "merge_ready": pull_request.get("mergeStateStatus")
                                == "CLEAN",
                            }
                        )
                page_info = connection["pageInfo"]
                if not page_info["hasNextPage"]:
                    break
                after = page_info["endCursor"]
                if not isinstance(after, str) or not after:
                    raise ValueError("missing cursor for next pull-request page")
                if after in continuation_cursors:
                    raise ValueError("repeated cursor for next pull-request page")
                continuation_cursors.add(after)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            await self._record_pull_request_metric_error(result, error)
        except (KeyError, TypeError, ValueError) as error:
            await self._record_pull_request_metric_error(
                result, GitHubApiError(f"malformed pull-request response: {error}")
            )
        else:
            result.results.update(count_metrics)
            result.results.update(
                {
                    "oldest_dependabot_pull_request_created_at": (
                        oldest["dependabot"][1] if "dependabot" in oldest else None
                    ),
                    "oldest_other_pull_request_created_at": (
                        oldest["other"][1] if "other" in oldest else None
                    ),
                }
            )
            result.results[_DEPENDABOT_PULL_REQUESTS_KEY] = dependabot_pull_requests

    async def _record_pull_request_metric_error(
        self, result: RepoResult, error: GitHubApiError
    ) -> None:
        await self._monitor.send_event(
            FeedbackEvent(
                "fetch", "error", f"failed to fetch open pull requests: {error}"
            )
        )
        for key in _PULL_REQUEST_METRIC_KEYS:
            result.results[key] = None
        result.results[_DEPENDABOT_PULL_REQUESTS_KEY] = None
        result.errors.append(f"open pull requests: {error}")


@dataclass(slots=True)
class IssuesCollectionReport:
    labels: bool = False
    results: list[RepoResult] = field(default_factory=list)
    dates: bool = False

    def add(self, result: RepoResult) -> None:
        self.results.append(result)

    def document(self) -> dict[str, object]:
        return {
            "summary": _summary(self.results),
            "repositories": [
                {
                    "owner": result.owner,
                    "repo": result.repo,
                    "repository": f"{result.owner}/{result.repo}",
                    "open_item_count": result.results.get("open_item_count"),
                    **_pull_request_metrics(result),
                    _DEPENDABOT_PULL_REQUESTS_KEY: result.results.get(
                        _DEPENDABOT_PULL_REQUESTS_KEY
                    ),
                    "items": [
                        _item_json(item, self.labels) for item in _item_records(result)
                    ],
                }
                for result in self.results
            ],
        }

    def render(self, format: str = "plain") -> str:
        style = ReportStyle.from_format(format)
        if isinstance(style, JSONReportStyle):
            return style.render_document(self.document())
        lines = _summary_lines(self.results)
        active = _repos_to_show(self.results)
        if isinstance(style, PlainReportStyle):
            for result in active:
                lines.extend(
                    [
                        "",
                        f"{result.owner}/{result.repo}  ({result.results.get('open_item_count')} open)",
                        *_pull_request_metric_lines(result, indent="  "),
                        *[
                            "  " + _item_plain_line(item, self.labels, dates=self.dates)
                            for item in _item_records(result)
                        ],
                    ]
                )
            return style.render_lines(lines)
        rows = [(result, item) for result in active for item in _item_records(result)]
        if rows:
            lines.extend(
                [
                    "",
                    _table_header(self.labels, self.dates),
                    _table_separator(self.labels, self.dates),
                ]
            )
            lines.extend(
                _table_row(result, item, self.labels, self.dates)
                for result, item in rows
            )
        assert isinstance(style, TableReportStyle)
        return style.render_lines(lines)


@dataclass(frozen=True, slots=True)
class IssuesMode:
    name: str = "issues"
    processor_type: type = IssuesRepoProcessor
    combine_key: str = "020"

    @property
    def command(self) -> click.Command:
        return issues

    def new_collection(self, options: dict) -> IssuesCollectionReport:
        return IssuesCollectionReport(
            labels=bool(options.get("labels", False)),
            dates=bool(options.get("dates", False)),
        )

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type=None):
        return IssuesRepoProcessor(
            owner, repo, gh, monitor, options=options, owner_type=owner_type
        )


MODE = IssuesMode()


@click.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option(
    "--labels",
    "show_labels",
    is_flag=True,
    default=False,
    help="Include issue labels in the report",
)
@click.option(
    "--dates",
    "show_dates",
    is_flag=True,
    default=False,
    help="Include item creation dates in local time",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the final report to a file",
)
@click.pass_context
def issues(
    ctx: click.Context,
    format_plain: bool,
    format_table: bool,
    format_json: bool,
    show_labels: bool,
    show_dates: bool,
    output: Path | None,
) -> None:
    """Scan repositories for open issues and pull requests."""
    selected_format = output_format(
        plain=format_plain, table=format_table, json_format=format_json
    )
    options = {
        "format": selected_format,
        "labels": show_labels,
        "dates": show_dates,
    }
    try:
        collection = asyncio.run(run_mode(ctx.obj["cfg"], MODE, options))
    except FatalError as error:
        log.error(error.message)
        sys.exit(error.exit_code)
    write_report(collection.render(selected_format), output)
    if getattr(collection, "abort_reason", None) == "rate_limited":
        log.error("rate limited; wrote incomplete report")
        sys.exit(4)


def _item_type(item: dict[str, Any]) -> str:
    return "pr" if "pull_request" in item else "issue"


def _pull_request_connection(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("response is not an object")
    repository = data.get("repository")
    if not isinstance(repository, dict):
        raise TypeError("repository is missing")
    connection = repository.get("pullRequests")
    if not isinstance(connection, dict):
        raise TypeError("pullRequests is missing")
    nodes = connection.get("nodes")
    if not isinstance(nodes, list) or not all(isinstance(node, dict) for node in nodes):
        raise ValueError("pull-request nodes are invalid")
    page_info = connection.get("pageInfo")
    if not isinstance(page_info, dict) or not isinstance(
        page_info.get("hasNextPage"), bool
    ):
        raise TypeError("pull-request page info is invalid")
    return connection


def _pull_request_data(
    pull_request: dict[str, Any],
) -> tuple[int, str, str, bool, datetime]:
    number = pull_request.get("number")
    created_at = pull_request.get("createdAt")
    url = pull_request.get("url")
    draft = pull_request.get("isDraft")
    if not isinstance(number, int) or isinstance(number, bool):
        raise TypeError("pull-request number is invalid")
    if not isinstance(created_at, str) or not created_at:
        raise TypeError("pull-request creation timestamp is invalid")
    if not isinstance(url, str) or not url:
        raise TypeError("pull-request URL is invalid")
    if not isinstance(draft, bool):
        raise TypeError("pull-request draft state is invalid")
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError as error:
        raise ValueError("pull-request creation timestamp is invalid") from error
    if created.tzinfo is None:
        raise ValueError("pull-request creation timestamp is timezone-naive")
    return number, created_at, url, draft, created


def _item_labels(item: dict[str, Any]) -> list[str]:
    return [
        label["name"]
        for label in (item.get("labels") or [])
        if isinstance(label, dict) and label.get("name")
    ]


def _item_record(item: dict[str, Any]) -> dict[str, Any]:
    item_type = _item_type(item)
    user = item.get("user")
    return {
        "number": item["number"],
        "title": item.get("title") or "",
        "type": item_type,
        "labels": _item_labels(item),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "url": item.get("html_url"),
        "author": user.get("login") if isinstance(user, dict) else None,
        "draft": item.get("draft") if item_type == "pr" else None,
    }


def _issues_activity_message(result: RepoResult) -> str | None:
    count = result.results.get("open_item_count")
    return f"found {count} open items" if count else None


def _has_open_items(result: RepoResult) -> bool:
    return bool(result.results.get("open_item_count"))


def _item_records(result: RepoResult) -> list[dict]:
    return result.results.get("open_items") or []


def _type_total(results: list[RepoResult], item_type: str) -> int | None:
    counts = [
        None
        if result.results.get("open_items") is None
        else sum(1 for item in _item_records(result) if item.get("type") == item_type)
        for result in results
    ]
    return (
        None
        if all(count is None for count in counts)
        else sum(count for count in counts if count is not None)
    )


def _summary(results: list[RepoResult]) -> dict[str, object]:
    return {
        "repos_scanned": len(results),
        "repos_with_items": sum(1 for result in results if _has_open_items(result)),
        "open_issues": _type_total(results, "issue"),
        "open_prs": _type_total(results, "pr"),
        **{
            key: _pull_request_metric_total(results, key)
            for key in _PULL_REQUEST_COUNT_METRIC_KEYS
        },
        **{
            key: _oldest_pull_request_timestamp(results, key)
            for key in _PULL_REQUEST_AGE_METRIC_KEYS
        },
        "pull_request_metrics_complete": _pull_request_metrics_complete(results),
    }


def _summary_lines(results: list[RepoResult]) -> list[str]:
    summary = _summary(results)
    return [
        _fmt("Repos scanned:", _display(summary["repos_scanned"])),
        _fmt("Repos with open items:", _display(summary["repos_with_items"])),
        _fmt("Open issues:", _display(summary["open_issues"])),
        _fmt("Open PRs:", _display(summary["open_prs"])),
        _fmt(
            "Dependabot PRs:",
            _display(summary["dependabot_open_pull_requests"]),
        ),
        _fmt(
            "Dependabot merge-ready PRs:",
            _display(summary["dependabot_merge_ready_pull_requests"]),
        ),
        _fmt("Other PRs:", _display(summary["other_open_pull_requests"])),
        _fmt(
            "Other merge-ready PRs:",
            _display(summary["other_merge_ready_pull_requests"]),
        ),
        *(
            []
            if summary["pull_request_metrics_complete"]
            else ["Pull-request metrics unavailable: incomplete repository data"]
        ),
    ]


def _repos_to_show(results: list[RepoResult]) -> list[RepoResult]:
    return sorted(
        (result for result in results if _has_open_items(result)),
        key=lambda result: f"{result.owner}/{result.repo}",
    )


def _item_plain_line(item: dict, labels: bool, *, dates: bool = False) -> str:
    date_prefix = f"{_format_local_timestamp(item.get('created_at'))} " if dates else ""
    line = f"#{item['number']} [{item['type']}] {date_prefix}{item['title']}"
    if labels and item.get("labels"):
        line += " " + " ".join(f"+{name}" for name in item["labels"])
    return line


def _item_json(item: dict, labels: bool) -> dict:
    value = {
        "number": item["number"],
        "title": item["title"],
        "type": item["type"],
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "url": item.get("url"),
        "author": item.get("author"),
        "draft": item.get("draft"),
    }
    if labels:
        value["labels"] = list(item.get("labels") or [])
    return value


def _pull_request_metrics(result: RepoResult) -> dict[str, object]:
    return {key: result.results.get(key) for key in _PULL_REQUEST_METRIC_KEYS}


def _pull_request_metric_total(results: list[RepoResult], key: str) -> int | None:
    values = [result.results.get(key) for result in results]
    return (
        None
        if any(value is None for value in values)
        else sum(value for value in values if isinstance(value, int))
    )


def _oldest_pull_request_timestamp(results: list[RepoResult], key: str) -> str | None:
    if not _pull_request_metrics_complete(results):
        return None
    timestamps = [
        value
        for result in results
        if isinstance((value := result.results.get(key)), str)
    ]
    return min(timestamps) if timestamps else None


def _pull_request_metrics_complete(results: list[RepoResult]) -> bool:
    return all(
        result.results.get(key) is not None
        for result in results
        for key in _PULL_REQUEST_COUNT_METRIC_KEYS
    )


def _pull_request_metric_lines(result: RepoResult, *, indent: str = "") -> list[str]:
    metrics = _pull_request_metrics(result)
    return [
        indent
        + _fmt("Dependabot PRs:", _display(metrics["dependabot_open_pull_requests"])),
        indent
        + _fmt(
            "Dependabot merge-ready PRs:",
            _display(metrics["dependabot_merge_ready_pull_requests"]),
        ),
        indent + _fmt("Other PRs:", _display(metrics["other_open_pull_requests"])),
        indent
        + _fmt(
            "Other merge-ready PRs:",
            _display(metrics["other_merge_ready_pull_requests"]),
        ),
    ]


def _fmt(label: str, value: int | str) -> str:
    return f"{label:<26}{value:>8}"


def _display(value: object) -> int | str:
    return value if isinstance(value, int) else "N/A"


def _table_header(labels: bool, dates: bool) -> str:
    header = f"|{'Repository':<38}|{'#':>6}|{'Type':<5}|{'Description':<50}"
    header += (
        f"|{'Dependabot PRs':>16}|{'Dependabot ready':>18}"
        f"|{'Other PRs':>12}|{'Other ready':>12}"
    )
    if dates:
        header += f"|{'Created (local)':<22}"
    if labels:
        header += f"|{'Labels':<24}"
    return header + "|"


def _table_separator(labels: bool, dates: bool) -> str:
    separator = "|" + "|".join("-" * width for width in (38, 6, 5, 50, 16, 18, 12, 12))
    if dates:
        separator += "|" + "-" * 22
    if labels:
        separator += "|" + "-" * 24
    return separator + "|"


def _table_row(result: RepoResult, item: dict, labels: bool, dates: bool) -> str:
    metrics = _pull_request_metrics(result)
    row = (
        f"|{f'{result.owner}/{result.repo}':<38}|{item['number']:>6}|{item['type']:<5}"
        f"|{_truncate(item['title'], 50):<50}"
        f"|{_display(metrics['dependabot_open_pull_requests']):>16}"
        f"|{_display(metrics['dependabot_merge_ready_pull_requests']):>18}"
        f"|{_display(metrics['other_open_pull_requests']):>12}"
        f"|{_display(metrics['other_merge_ready_pull_requests']):>12}"
    )
    if dates:
        row += f"|{_format_local_timestamp(item.get('created_at')):<22}"
    if labels:
        row += f"|{', '.join(item.get('labels') or []):<24}"
    return row + "|"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _format_local_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "N/A"
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return "N/A"
    if timestamp.tzinfo is None:
        return "N/A"
    return timestamp.astimezone().strftime("%Y-%m-%d %H:%M %Z")
