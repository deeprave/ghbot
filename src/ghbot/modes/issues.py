"""Issue and pull-request scanning and reporting mode."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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


@dataclass(slots=True)
class IssuesCollectionReport:
    labels: bool = False
    results: list[RepoResult] = field(default_factory=list)

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
                        *[
                            "  " + _item_plain_line(item, self.labels)
                            for item in _item_records(result)
                        ],
                    ]
                )
            return style.render_lines(lines)
        rows = [
            (f"{result.owner}/{result.repo}", item)
            for result in active
            for item in _item_records(result)
        ]
        if rows:
            lines.extend(
                ["", _table_header(self.labels), _table_separator(self.labels)]
            )
            lines.extend(
                _table_row(repository, item, self.labels) for repository, item in rows
            )
        assert isinstance(style, TableReportStyle)
        return style.render_lines(lines)


@dataclass(frozen=True, slots=True)
class IssuesMode:
    name: str = "issues"
    processor_type: type = IssuesRepoProcessor

    def new_collection(self, options: dict) -> IssuesCollectionReport:
        return IssuesCollectionReport(labels=bool(options.get("labels", False)))

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type=None):
        return IssuesRepoProcessor(
            owner, repo, gh, monitor, options=options, owner_type=owner_type
        )


MODE = IssuesMode()


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


def _summary(results: list[RepoResult]) -> dict[str, int | None]:
    return {
        "repos_scanned": len(results),
        "repos_with_items": sum(1 for result in results if _has_open_items(result)),
        "open_issues": _type_total(results, "issue"),
        "open_prs": _type_total(results, "pr"),
    }


def _summary_lines(results: list[RepoResult]) -> list[str]:
    summary = _summary(results)
    return [
        _fmt("Repos scanned:", _display(summary["repos_scanned"])),
        _fmt("Repos with open items:", _display(summary["repos_with_items"])),
        _fmt("Open issues:", _display(summary["open_issues"])),
        _fmt("Open PRs:", _display(summary["open_prs"])),
    ]


def _repos_to_show(results: list[RepoResult]) -> list[RepoResult]:
    return sorted(
        (result for result in results if _has_open_items(result)),
        key=lambda result: f"{result.owner}/{result.repo}",
    )


def _item_plain_line(item: dict, labels: bool) -> str:
    line = f"#{item['number']} [{item['type']}] {item['title']}"
    if labels and item.get("labels"):
        line += " " + " ".join(f"+{name}" for name in item["labels"])
    return line


def _item_json(item: dict, labels: bool) -> dict:
    value = {"number": item["number"], "title": item["title"], "type": item["type"]}
    if labels:
        value["labels"] = list(item.get("labels") or [])
    return value


def _fmt(label: str, value: int | str) -> str:
    return f"{label:<26}{value:>8}"


def _display(value: int | None) -> int | str:
    return "N/A" if value is None else value


def _table_header(labels: bool) -> str:
    header = f"|{'Repository':<38}|{'#':>6}|{'Type':<5}|{'Description':<50}"
    if labels:
        header += f"|{'Labels':<24}"
    return header + "|"


def _table_separator(labels: bool) -> str:
    separator = "|" + "|".join("-" * width for width in (38, 6, 5, 50))
    if labels:
        separator += "|" + "-" * 24
    return separator + "|"


def _table_row(repository: str, item: dict, labels: bool) -> str:
    row = (
        f"|{repository:<38}|{item['number']:>6}|{item['type']:<5}"
        f"|{_truncate(item['title'], 50):<50}"
    )
    if labels:
        row += f"|{', '.join(item.get('labels') or []):<24}"
    return row + "|"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"
