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
from ghbot.modes.issues import IssuesRepoProcessor
from ghbot.processor import FeedbackEvent, RepoProcessor

_PULL_REQUEST_RESULT_KEYS = (
    "dependabot_open_pull_requests",
    "dependabot_merge_ready_pull_requests",
    "other_open_pull_requests",
    "other_merge_ready_pull_requests",
    "oldest_dependabot_pull_request_created_at",
    "oldest_other_pull_request_created_at",
)


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


def _graphql_pr(
    author="octocat",
    merge_state="CLEAN",
    *,
    number=1,
    created_at="2026-11-01T10:20:30Z",
    url="https://github.com/acme/widgets/pull/1",
    is_draft=False,
):
    return {
        "number": number,
        "author": None if author is None else {"login": author},
        "mergeStateStatus": merge_state,
        "createdAt": created_at,
        "url": url,
        "isDraft": is_draft,
    }


def _graphql_page(nodes, *, has_next_page=False, end_cursor=None):
    return {
        "repository": {
            "pullRequests": {
                "nodes": nodes,
                "pageInfo": {
                    "hasNextPage": has_next_page,
                    "endCursor": end_cursor,
                },
            }
        }
    }


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
    gh.graphql = AsyncMock(return_value=_graphql_page([]))
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
        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["open_item_count"] == 4
        assert [i["number"] for i in result.results["open_items"]] == [1, 2, 3, 4]

    @pytest.mark.anyio
    async def test_tags_each_item_type(self):
        gh = _make_gh(issues=[_issue(1), _pr_item(2), _issue(3)])
        processor, _ = _make_processor(gh)
        with patch("ghbot.modes.issues.github_api_call", _passthrough):
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
                _issue(
                    12,
                    "Fix the login redirect",
                    labels=["bug", "urgent"],
                    created_at="2026-11-01T10:20:30Z",
                    updated_at="2026-11-02T11:22:33Z",
                    html_url="https://github.com/acme/widgets/issues/12",
                    user={"login": "octocat"},
                ),
                _pr_item(
                    15,
                    "Add retry to fetch",
                    labels=["enhancement"],
                    created_at="2026-11-03T10:20:30Z",
                    updated_at="2026-11-04T11:22:33Z",
                    html_url="https://github.com/acme/widgets/pull/15",
                    user={"login": "dependabot[bot]"},
                    draft=True,
                ),
                _issue(3, "Flaky test on CI"),  # no labels field
            ]
        )
        processor, _ = _make_processor(gh)
        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["open_items"] == [
            {
                "number": 12,
                "title": "Fix the login redirect",
                "type": "issue",
                "labels": ["bug", "urgent"],
                "created_at": "2026-11-01T10:20:30Z",
                "updated_at": "2026-11-02T11:22:33Z",
                "url": "https://github.com/acme/widgets/issues/12",
                "author": "octocat",
                "draft": None,
            },
            {
                "number": 15,
                "title": "Add retry to fetch",
                "type": "pr",
                "labels": ["enhancement"],
                "created_at": "2026-11-03T10:20:30Z",
                "updated_at": "2026-11-04T11:22:33Z",
                "url": "https://github.com/acme/widgets/pull/15",
                "author": "dependabot[bot]",
                "draft": True,
            },
            {
                "number": 3,
                "title": "Flaky test on CI",
                "type": "issue",
                "labels": [],
                "created_at": None,
                "updated_at": None,
                "url": None,
                "author": None,
                "draft": None,
            },
        ]
        assert gh.getitem.await_count == 0

    @pytest.mark.anyio
    async def test_requests_open_issues_endpoint(self):
        gh = _make_gh(issues=[_issue(1)])
        processor, _ = _make_processor(gh)
        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            await processor.run()
        urls = [call.args[0] for call in gh.getiter.call_args_list]
        assert any("/issues?state=open" in url for url in urls)


class TestIssuesRepoProcessorPullRequestMetrics:
    @pytest.mark.anyio
    async def test_paginates_graphql_pull_requests_and_counts_categories(self):
        gh = _make_gh(issues=[_issue(1)])
        gh.graphql.side_effect = [
            _graphql_page(
                [
                    _graphql_pr("dependabot[bot]", "CLEAN"),
                    _graphql_pr("octocat", "BLOCKED"),
                ],
                has_next_page=True,
                end_cursor="cursor-1",
            ),
            _graphql_page(
                [
                    _graphql_pr("dependabot[bot]", "HAS_HOOKS"),
                    _graphql_pr(None, "CLEAN"),
                ]
            ),
        ]
        processor, _ = _make_processor(gh)

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.results["dependabot_open_pull_requests"] == 2
        assert result.results["dependabot_merge_ready_pull_requests"] == 1
        assert result.results["other_open_pull_requests"] == 2
        assert result.results["other_merge_ready_pull_requests"] == 1
        assert gh.graphql.await_count == 2
        assert gh.graphql.await_args_list[0].kwargs == {
            "owner": "acme",
            "repo": "widgets",
            "after": None,
        }
        assert gh.graphql.await_args_list[1].kwargs == {
            "owner": "acme",
            "repo": "widgets",
            "after": "cursor-1",
        }
        assert "pullRequests" in gh.graphql.await_args_list[0].args[0]
        assert gh.getitem.await_count == 0

    @pytest.mark.anyio
    async def test_collects_oldest_timestamps_and_dependabot_detail_across_pages(self):
        gh = _make_gh()
        gh.graphql.side_effect = [
            _graphql_page(
                [
                    _graphql_pr(
                        "dependabot[bot]",
                        "CLEAN",
                        number=12,
                        created_at="2026-11-03T10:20:30Z",
                        url="https://github.com/acme/widgets/pull/12",
                    ),
                    _graphql_pr(
                        "octocat",
                        "BLOCKED",
                        number=13,
                        created_at="2026-11-02T10:20:30Z",
                    ),
                ],
                has_next_page=True,
                end_cursor="cursor-1",
            ),
            _graphql_page(
                [
                    _graphql_pr(
                        "dependabot[bot]",
                        "DRAFT",
                        number=14,
                        created_at="2026-11-01T10:20:30Z",
                        url="https://github.com/acme/widgets/pull/14",
                        is_draft=True,
                    ),
                    _graphql_pr(
                        "octocat",
                        "CLEAN",
                        number=15,
                        created_at="2026-11-04T10:20:30Z",
                    ),
                ]
            ),
        ]
        processor, _ = _make_processor(gh)

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.results["oldest_dependabot_pull_request_created_at"] == (
            "2026-11-01T10:20:30Z"
        )
        assert result.results["oldest_other_pull_request_created_at"] == (
            "2026-11-02T10:20:30Z"
        )
        assert result.results["dependabot_pull_requests"] == [
            {
                "number": 12,
                "url": "https://github.com/acme/widgets/pull/12",
                "created_at": "2026-11-03T10:20:30Z",
                "draft": False,
                "merge_ready": True,
            },
            {
                "number": 14,
                "url": "https://github.com/acme/widgets/pull/14",
                "created_at": "2026-11-01T10:20:30Z",
                "draft": True,
                "merge_ready": False,
            },
        ]
        assert "number" in gh.graphql.await_args_list[0].args[0]
        assert "createdAt" in gh.graphql.await_args_list[0].args[0]
        assert "isDraft" in gh.graphql.await_args_list[0].args[0]

    @pytest.mark.anyio
    async def test_empty_dependabot_category_has_an_empty_detail_list(self):
        processor, _ = _make_processor()

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.results["dependabot_pull_requests"] == []
        assert result.results["oldest_dependabot_pull_request_created_at"] is None

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "merge_state",
        ["HAS_HOOKS", "BLOCKED", "DIRTY", "DRAFT", "UNKNOWN", None],
    )
    async def test_only_clean_pull_requests_are_merge_ready(self, merge_state):
        gh = _make_gh()
        gh.graphql.return_value = _graphql_page(
            [_graphql_pr("dependabot[bot]", merge_state)]
        )
        processor, _ = _make_processor(gh)

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.results["dependabot_open_pull_requests"] == 1
        assert result.results["dependabot_merge_ready_pull_requests"] == 0


class TestIssuesRepoProcessorPullRequestMetricFailures:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "pull_request",
        [
            _graphql_pr(number=None),
            _graphql_pr(created_at="not-a-timestamp"),
            _graphql_pr(url=""),
            _graphql_pr(is_draft=None),
        ],
        ids=["missing-number", "invalid-timestamp", "missing-url", "missing-draft"],
    )
    async def test_malformed_detail_marks_all_pull_request_metrics_unavailable(
        self, pull_request
    ):
        gh = _make_gh()
        gh.graphql.return_value = _graphql_page([pull_request])
        processor, _ = _make_processor(gh)

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.status == "partial"
        assert all(result.results[key] is None for key in _PULL_REQUEST_RESULT_KEYS)
        assert result.results["dependabot_pull_requests"] is None

    @pytest.mark.anyio
    async def test_repeated_pagination_cursor_marks_metrics_unavailable(self):
        gh = _make_gh(issues=[_issue(1)])
        gh.graphql.side_effect = [
            _graphql_page([], has_next_page=True, end_cursor="cursor-1"),
            _graphql_page([], has_next_page=True, end_cursor="cursor-1"),
            AssertionError("repeated cursor must not request another page"),
        ]
        processor, monitor = _make_processor(gh)

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.status == "partial"
        assert gh.graphql.await_count == 2
        assert all(
            result.results[key] is None
            for key in (
                "dependabot_open_pull_requests",
                "dependabot_merge_ready_pull_requests",
                "other_open_pull_requests",
                "other_merge_ready_pull_requests",
            )
        )
        assert any(
            event.type == "fetch" and event.severity == "error"
            for event in monitor.events
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "graphql_result",
        [
            GitHubApiError("query failed"),
            {"repository": {}},
            _graphql_page("not a list"),
            _graphql_page([None]),
            _graphql_page([], has_next_page="yes"),
            _graphql_page([], has_next_page=True),
            _graphql_page([], has_next_page=True, end_cursor=""),
        ],
        ids=[
            "api-error",
            "missing-pull-requests",
            "nodes-not-list",
            "nodes-not-objects",
            "has-next-not-bool",
            "next-page-missing-cursor",
            "next-page-empty-cursor",
        ],
    )
    async def test_recoverable_failure_marks_metrics_unavailable(self, graphql_result):
        gh = _make_gh(issues=[_issue(1)])
        if isinstance(graphql_result, Exception):
            gh.graphql.side_effect = graphql_result
        else:
            gh.graphql.return_value = graphql_result
        processor, monitor = _make_processor(gh)

        with patch("ghbot.modes.issues.github_api_call", _passthrough):
            result = await processor.run()

        assert result.status == "partial"
        assert result.errors
        assert {
            key: result.results[key]
            for key in (
                "dependabot_open_pull_requests",
                "dependabot_merge_ready_pull_requests",
                "other_open_pull_requests",
                "other_merge_ready_pull_requests",
                "oldest_dependabot_pull_request_created_at",
                "oldest_other_pull_request_created_at",
            )
        } == {
            "dependabot_open_pull_requests": None,
            "dependabot_merge_ready_pull_requests": None,
            "other_open_pull_requests": None,
            "other_merge_ready_pull_requests": None,
            "oldest_dependabot_pull_request_created_at": None,
            "oldest_other_pull_request_created_at": None,
        }
        assert result.results["dependabot_pull_requests"] is None
        assert any(
            event.type == "fetch" and event.severity == "error"
            for event in monitor.events
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        "error_type",
        [GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError],
    )
    async def test_rate_limits_from_graphql_propagate(self, error_type):
        gh = _make_gh()
        gh.graphql.side_effect = error_type("rate limited")
        processor, _ = _make_processor(gh)

        with (
            patch("ghbot.modes.issues.github_api_call", _passthrough),
            pytest.raises(error_type),
        ):
            await processor.run()


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
        gh.graphql = AsyncMock(return_value=_graphql_page([]))
        return gh

    @pytest.mark.anyio
    async def test_not_found_sets_none_without_error(self):
        processor, _ = _make_processor(self._make_gh_not_found())
        with patch("ghbot.modes.issues.github_api_call", _passthrough):
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
        gh.graphql = AsyncMock(return_value=_graphql_page([]))
        return gh

    @pytest.mark.anyio
    async def test_api_error_sets_none_and_partial(self):
        processor, _ = _make_processor(self._make_gh_api_error())
        with patch("ghbot.modes.issues.github_api_call", _passthrough):
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
            patch("ghbot.modes.issues.github_api_call", _passthrough),
            pytest.raises(GitHubPrimaryRateLimitError),
        ):
            await processor.run()

    @pytest.mark.anyio
    async def test_secondary_rate_limit_reraises(self):
        processor, _ = _make_processor(
            self._make_gh_raising(GitHubSecondaryRateLimitError("slow down"))
        )
        with (
            patch("ghbot.modes.issues.github_api_call", _passthrough),
            pytest.raises(GitHubSecondaryRateLimitError),
        ):
            await processor.run()
