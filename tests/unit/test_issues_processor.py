"""Tests for IssuesRepoProcessor."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.processor import FeedbackEvent, IssuesRepoProcessor, RepoProcessor


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[FeedbackEvent] = []

    async def send_event(self, event: FeedbackEvent) -> None:
        self.events.append(event)


async def _aiter(*items):
    for item in items:
        yield item


def _issue(number, title="Title", labels=None, **extra):
    item: dict = {"number": number, "title": title}
    if labels is not None:
        item["labels"] = [{"name": name} for name in labels]
    item.update(extra)
    return item


def _pr_item(number, title="A pull request", labels=None, **extra):
    item = _issue(number, title, labels, **extra)
    item["pull_request"] = {"url": "u"}
    return item


@asynccontextmanager
async def _passthrough(gh):
    yield


def _make_gh(issues=None):
    """gh mock where the open-issues endpoint returns the given items."""
    gh = MagicMock()
    issues = [] if issues is None else issues

    def _getiter(url, *, url_vars=None):
        if "/issues?state=open" in url:
            return _aiter(*issues)
        return _aiter()

    gh.getiter = MagicMock(side_effect=_getiter)
    gh.getitem = AsyncMock(side_effect=lambda url, *, url_vars=None: {})
    return gh


def _make_processor(gh=None, monitor=None):
    gh = gh or _make_gh()
    monitor = monitor or RecordingMonitor()
    return IssuesRepoProcessor(
        owner="acme", repo="widgets", gh=gh, monitor=monitor
    ), monitor


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestIssuesRepoProcessorConstructor:
    def test_empty_owner_raises(self):
        with pytest.raises(ValueError, match="owner"):
            IssuesRepoProcessor(
                owner="", repo="widgets", gh=MagicMock(), monitor=RecordingMonitor()
            )

    def test_empty_repo_raises(self):
        with pytest.raises(ValueError, match="repo"):
            IssuesRepoProcessor(
                owner="acme", repo="", gh=MagicMock(), monitor=RecordingMonitor()
            )

    def test_isinstance_repo_processor(self):
        processor, _ = _make_processor()
        assert isinstance(processor, RepoProcessor)

    def test_owner_and_repo_properties(self):
        processor, _ = _make_processor()
        assert processor.owner == "acme"
        assert processor.repo == "widgets"


# ---------------------------------------------------------------------------
# Open-issue collection
# ---------------------------------------------------------------------------


class TestIssuesRepoProcessorCollection:
    @pytest.mark.anyio
    async def test_counts_open_items_including_pull_requests(self):
        gh = _make_gh(issues=[_issue(1), _pr_item(2), _issue(3), _pr_item(4)])
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["open_item_count"] == 4
        assert [i["number"] for i in result.results["open_items"]] == [1, 2, 3, 4]

    @pytest.mark.anyio
    async def test_tags_each_item_type(self):
        gh = _make_gh(issues=[_issue(1), _pr_item(2), _issue(3)])
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert [(i["number"], i["type"]) for i in result.results["open_items"]] == [
            (1, "issue"),
            (2, "pr"),
            (3, "issue"),
        ]

    @pytest.mark.anyio
    async def test_records_carry_number_title_type_labels_in_order(self):
        gh = _make_gh(
            issues=[
                _issue(12, "Fix the login redirect", labels=["bug", "urgent"]),
                _pr_item(15, "Add retry to fetch", labels=["enhancement"]),
                _issue(3, "Flaky test on CI"),  # no labels field
            ]
        )
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["open_items"] == [
            {
                "number": 12,
                "title": "Fix the login redirect",
                "type": "issue",
                "labels": ["bug", "urgent"],
            },
            {
                "number": 15,
                "title": "Add retry to fetch",
                "type": "pr",
                "labels": ["enhancement"],
            },
            {"number": 3, "title": "Flaky test on CI", "type": "issue", "labels": []},
        ]

    @pytest.mark.anyio
    async def test_requests_open_issues_endpoint(self):
        gh = _make_gh(issues=[_issue(1)])
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            await processor.run()
        urls = [call.args[0] for call in gh.getiter.call_args_list]
        assert any("/issues?state=open" in url for url in urls)


# ---------------------------------------------------------------------------
# GitHubNotFoundError — unavailable (403/404)
# ---------------------------------------------------------------------------


class TestIssuesRepoProcessorNotFound:
    def _make_gh_not_found(self):
        gh = MagicMock()

        def _getiter(url, *, url_vars=None):
            if "/issues" in url:

                async def _fail():
                    raise GitHubNotFoundError("not found")
                    yield

                return _fail()
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        return gh

    @pytest.mark.anyio
    async def test_not_found_sets_none_without_error(self):
        processor, _ = _make_processor(self._make_gh_not_found())
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["open_item_count"] is None
        assert result.results["open_items"] is None
        assert result.errors == []
        assert result.status == "success"


# ---------------------------------------------------------------------------
# GitHubApiError — partial result
# ---------------------------------------------------------------------------


class TestIssuesRepoProcessorApiError:
    def _make_gh_api_error(self):
        gh = MagicMock()

        def _getiter(url, *, url_vars=None):
            if "/issues" in url:

                async def _fail():
                    raise GitHubApiError("api error")
                    yield

                return _fail()
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        return gh

    @pytest.mark.anyio
    async def test_api_error_sets_none_and_partial(self):
        processor, _ = _make_processor(self._make_gh_api_error())
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["open_item_count"] is None
        assert result.results["open_items"] is None
        assert result.status == "partial"
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# FatalError propagation
# ---------------------------------------------------------------------------


class TestIssuesRepoProcessorFatalErrors:
    def _make_gh_raising(self, exc):
        gh = MagicMock()

        def _getiter(url, *, url_vars=None):
            async def _fail():
                raise exc
                yield

            return _fail()

        gh.getiter = MagicMock(side_effect=_getiter)
        return gh

    @pytest.mark.anyio
    async def test_primary_rate_limit_reraises(self):
        processor, _ = _make_processor(
            self._make_gh_raising(GitHubPrimaryRateLimitError("rate limited"))
        )
        with (
            patch("ghbot.processor.github_api_call", _passthrough),
            pytest.raises(GitHubPrimaryRateLimitError),
        ):
            await processor.run()

    @pytest.mark.anyio
    async def test_secondary_rate_limit_reraises(self):
        processor, _ = _make_processor(
            self._make_gh_raising(GitHubSecondaryRateLimitError("slow down"))
        )
        with (
            patch("ghbot.processor.github_api_call", _passthrough),
            pytest.raises(GitHubSecondaryRateLimitError),
        ):
            await processor.run()
