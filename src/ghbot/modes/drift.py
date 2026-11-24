"""Release-drift scanning and reporting mode."""

from __future__ import annotations

import asyncio
import sys
from base64 import b64decode
from dataclasses import dataclass, field
from pathlib import Path

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


class DriftRepoProcessor:
    """Find commits on a repository's default branch since its stable release."""

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
        self._owner, self._repo, self._gh, self._monitor = owner, repo, gh, monitor
        self._options, self._owner_type = dict(options or {}), owner_type
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
        result.results.update(
            {
                "latest_release_tag": None,
                "latest_release_published_at": None,
                "default_branch": None,
                "commits_since_release": None,
                "pypi_publishing_configured": None,
            }
        )
        try:
            if (
                await self._fetch_release(result)
                and await self._fetch_default_branch(result)
                and await self._fetch_drift(result)
                and result.results["commits_since_release"] > 0
            ):
                await self._detect_pypi_configuration(result)
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
            if commits := result.results["commits_since_release"]:
                await self._monitor.send_event(
                    FeedbackEvent(
                        "progress",
                        "info",
                        f"found {commits} commits since {result.results['latest_release_tag']}",
                    )
                )
                for event in self._deferred_events:
                    await self._monitor.send_event(event)
        return result

    async def _fetch_release(self, result: RepoResult) -> bool:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching latest release")
        )
        try:
            async with github_api_call(self._gh):
                release = await self._gh.getitem(
                    "/repos/{owner}/{repo}/releases/latest",
                    url_vars={"owner": self._owner, "repo": self._repo},
                )
            result.results["latest_release_tag"] = release.get("tag_name")
            result.results["latest_release_published_at"] = release.get("published_at")
            return bool(result.results["latest_release_tag"])
        except GitHubNotFoundError:
            await self._defer_event(
                FeedbackEvent("fetch", "debug", "no stable release available")
            )
            return False
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            await self._record_error(result, "latest release", error)
            return False

    async def _fetch_default_branch(self, result: RepoResult) -> bool:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "fetching repository metadata")
        )
        try:
            async with github_api_call(self._gh):
                repository = await self._gh.getitem(
                    "/repos/{owner}/{repo}",
                    url_vars={"owner": self._owner, "repo": self._repo},
                )
            result.results["default_branch"] = repository.get("default_branch")
            return bool(result.results["default_branch"])
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            await self._record_error(result, "repository metadata", error)
            return False

    async def _fetch_drift(self, result: RepoResult) -> bool:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "comparing release to default branch")
        )
        basehead = f"{result.results['latest_release_tag']}...{result.results['default_branch']}"
        try:
            async with github_api_call(self._gh):
                comparison = await self._gh.getitem(
                    "/repos/{owner}/{repo}/compare/{basehead}",
                    url_vars={
                        "owner": self._owner,
                        "repo": self._repo,
                        "basehead": basehead,
                    },
                )
            result.results["commits_since_release"] = comparison.get("ahead_by")
            return isinstance(result.results["commits_since_release"], int)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            await self._record_error(result, "release comparison", error)
            return False

    async def _detect_pypi_configuration(self, result: RepoResult) -> None:
        await self._defer_event(
            FeedbackEvent("progress", "debug", "checking PyPI workflow configuration")
        )
        try:
            async with github_api_call(self._gh):
                tree = await self._gh.getitem(
                    "/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                    url_vars={
                        "owner": self._owner,
                        "repo": self._repo,
                        "branch": result.results["default_branch"],
                    },
                )
            if tree.get("truncated"):
                await self._record_error(
                    result,
                    "PyPI workflow configuration",
                    ValueError("workflow tree listing was truncated"),
                )
                return
            workflows = [
                item
                for item in tree.get("tree", [])
                if item.get("type") == "blob"
                and item.get("path", "").startswith(".github/workflows/")
                and item.get("path", "").endswith((".yml", ".yaml"))
            ]
            for workflow in workflows:
                path = workflow["path"]
                if "pypi" in path.lower():
                    result.results["pypi_publishing_configured"] = True
                    return
                async with github_api_call(self._gh):
                    blob = await self._gh.getitem(
                        "/repos/{owner}/{repo}/git/blobs/{sha}",
                        url_vars={
                            "owner": self._owner,
                            "repo": self._repo,
                            "sha": workflow["sha"],
                        },
                    )
                if (
                    "pypi"
                    in b64decode(blob.get("content", ""))
                    .decode("utf-8", errors="replace")
                    .lower()
                ):
                    result.results["pypi_publishing_configured"] = True
                    return
            result.results["pypi_publishing_configured"] = False
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except (GitHubApiError, ValueError) as error:
            await self._record_error(result, "PyPI workflow configuration", error)

    async def _defer_event(self, event: FeedbackEvent) -> None:
        self._deferred_events.append(event)

    async def _record_error(
        self, result: RepoResult, operation: str, error: Exception
    ) -> None:
        result.errors.append(f"{operation}: {error}")
        await self._monitor.send_event(
            FeedbackEvent("fetch", "error", f"failed to fetch {operation}: {error}")
        )


@dataclass(slots=True)
class DriftCollectionReport:
    results: list[RepoResult] = field(default_factory=list)

    def add(self, result: RepoResult) -> None:
        self.results.append(result)

    def document(self) -> dict[str, object]:
        reportable = _reportable(self.results)
        return {
            "summary": _summary(self.results),
            "repositories": [_repo_document(result) for result in reportable],
        }

    def render(self, format: str = "plain") -> str:
        style = ReportStyle.from_format(format)
        if isinstance(style, JSONReportStyle):
            return style.render_document(self.document())
        lines = _summary_lines(self.results)
        reportable = _reportable(self.results)
        if isinstance(style, PlainReportStyle):
            for result in reportable:
                lines.extend(
                    [
                        "",
                        f"{result.owner}/{result.repo}",
                        _fmt("  Latest release:", result.results["latest_release_tag"]),
                        _fmt(
                            "  Release published:",
                            _display(result.results["latest_release_published_at"]),
                        ),
                        _fmt("  Default branch:", result.results["default_branch"]),
                        _fmt(
                            "  Commits since release:",
                            result.results["commits_since_release"],
                        ),
                        _fmt(
                            "  PyPI configured:",
                            _pypi(result.results["pypi_publishing_configured"]),
                        ),
                    ]
                )
            return style.render_lines(lines)
        assert isinstance(style, TableReportStyle)
        if reportable:
            lines.extend(["", _table_header(), _table_separator()])
            lines.extend(_table_row(result) for result in reportable)
        return style.render_lines(lines)


@dataclass(frozen=True, slots=True)
class DriftMode:
    name: str = "drift"
    processor_type: type = DriftRepoProcessor
    combine_key: str = "030"

    @property
    def command(self) -> click.Command:
        return drift

    def new_collection(self, options: dict) -> DriftCollectionReport:
        return DriftCollectionReport()

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type=None):
        return DriftRepoProcessor(
            owner, repo, gh, monitor, options=options, owner_type=owner_type
        )


MODE = DriftMode()


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
def drift(
    ctx: click.Context,
    format_plain: bool,
    format_table: bool,
    format_json: bool,
    output: Path | None,
) -> None:
    """Report commits since each repository's latest stable release."""
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
    if getattr(collection, "abort_reason", None) == "rate_limited":
        log.error("rate limited; wrote incomplete report")
        sys.exit(4)


def _reportable(results: list[RepoResult]) -> list[RepoResult]:
    return sorted(
        (
            result
            for result in results
            if isinstance(result.results.get("commits_since_release"), int)
            and result.results["commits_since_release"] > 0
        ),
        key=lambda result: f"{result.owner}/{result.repo}",
    )


def _summary(results: list[RepoResult]) -> dict[str, int]:
    reportable = _reportable(results)
    return {
        "repos_scanned": len(results),
        "released_repos": sum(
            1 for result in results if result.results.get("latest_release_tag")
        ),
        "repos_with_drift": len(reportable),
        "commits_since_release": sum(
            result.results["commits_since_release"] for result in reportable
        ),
    }


def _summary_lines(results: list[RepoResult]) -> list[str]:
    summary = _summary(results)
    return [
        _fmt("Repos scanned:", summary["repos_scanned"]),
        _fmt("Released repos:", summary["released_repos"]),
        _fmt("Repos with drift:", summary["repos_with_drift"]),
        _fmt("Commits since release:", summary["commits_since_release"]),
    ]


def _repo_document(result: RepoResult) -> dict[str, object]:
    return {
        "owner": result.owner,
        "repo": result.repo,
        "repository": f"{result.owner}/{result.repo}",
        "default_branch": result.results["default_branch"],
        "latest_release_tag": result.results["latest_release_tag"],
        "latest_release_published_at": result.results["latest_release_published_at"],
        "commits_since_release": result.results["commits_since_release"],
        "pypi_publishing_configured": result.results["pypi_publishing_configured"],
    }


def _fmt(label: str, value: object) -> str:
    return f"{label:<26}{value!s:>8}"


def _display(value: object) -> object:
    return "N/A" if value is None else value


def _pypi(value: bool | None) -> str:
    return "N/A" if value is None else "yes" if value else "no"


def _table_header() -> str:
    return f"|{'Repository':<32}|{' Release':>14}|{' Published':>22}|{' Branch':>14}|{' Commits':>10}|{' PyPI':>8}|"


def _table_separator() -> str:
    return "|" + "|".join("-" * width for width in (32, 14, 22, 14, 10, 8)) + "|"


def _table_row(result: RepoResult) -> str:
    return f"|{f'{result.owner}/{result.repo}':<32}|{_display(result.results['latest_release_tag']):>14}|{_display(result.results['latest_release_published_at']):>22}|{_display(result.results['default_branch']):>14}|{result.results['commits_since_release']:>10}|{_pypi(result.results['pypi_publishing_configured']):>8}|"
