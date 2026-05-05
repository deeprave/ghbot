"""Tests for SecurityRepoProcessor."""

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.processor import FeedbackEvent, RepoProcessor, SecurityRepoProcessor


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[FeedbackEvent] = []

    async def send_event(self, event: FeedbackEvent) -> None:
        self.events.append(event)


async def _aiter(*items):
    for item in items:
        yield item


@asynccontextmanager
async def _passthrough(gh):
    yield


def _make_gh(dependabot=3, code_scanning=2, secret_scanning=1):
    """gh mock where each security endpoint returns the given number of items."""
    gh = MagicMock()

    def _getiter(url, *, url_vars=None):
        if "dependabot" in url:
            return _aiter(*[{}] * dependabot)
        if "code-scanning" in url:
            return _aiter(*[{}] * code_scanning)
        if "secret-scanning" in url:
            return _aiter(*[{}] * secret_scanning)
        return _aiter()

    gh.getiter = MagicMock(side_effect=_getiter)
    return gh


def _make_processor(gh=None, monitor=None):
    gh = gh or _make_gh()
    monitor = monitor or RecordingMonitor()
    return SecurityRepoProcessor(
        owner="acme", repo="widgets", gh=gh, monitor=monitor
    ), monitor


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestSecurityRepoProcessorConstructor:
    def test_empty_owner_raises(self):
        with pytest.raises(ValueError, match="owner"):
            SecurityRepoProcessor(
                owner="", repo="widgets", gh=MagicMock(), monitor=RecordingMonitor()
            )

    def test_empty_repo_raises(self):
        with pytest.raises(ValueError, match="repo"):
            SecurityRepoProcessor(
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
# Happy path
# ---------------------------------------------------------------------------


class TestSecurityRepoProcessorHappyPath:
    @pytest.mark.anyio
    async def test_run_returns_success_status(self):
        processor, _ = _make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.status == "success"

    @pytest.mark.anyio
    async def test_run_stores_counts(self):
        processor, _ = _make_processor(
            _make_gh(dependabot=3, code_scanning=2, secret_scanning=1)
        )
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["dependabot_alerts"] == 3
        assert result.results["code_scanning_alerts"] == 2
        assert result.results["secret_scanning_alerts"] == 1

    @pytest.mark.anyio
    async def test_run_returns_correct_owner_and_repo(self):
        processor, _ = _make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.owner == "acme"
        assert result.repo == "widgets"

    @pytest.mark.anyio
    async def test_run_no_errors(self):
        processor, _ = _make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.errors == []

    @pytest.mark.anyio
    async def test_run_emits_found_issues_with_total_count(self):
        processor, monitor = _make_processor(
            _make_gh(dependabot=3, code_scanning=2, secret_scanning=1)
        )
        with patch("ghbot.processor.github_api_call", _passthrough):
            await processor.run()
        info_events = [e for e in monitor.events if e.severity == "info"]
        assert [e.message for e in info_events] == ["found issues 6"]

    @pytest.mark.anyio
    async def test_run_does_not_emit_processing_started(self):
        processor, monitor = _make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough):
            await processor.run()
        assert all(e.message != "processing started" for e in monitor.events)

    @pytest.mark.anyio
    async def test_run_with_zero_issues_emits_no_repository_events(self):
        processor, monitor = _make_processor(
            _make_gh(dependabot=0, code_scanning=0, secret_scanning=0)
        )
        with patch("ghbot.processor.github_api_call", _passthrough):
            await processor.run()
        assert monitor.events == []


# ---------------------------------------------------------------------------
# 403/404 — unavailable endpoints
# ---------------------------------------------------------------------------


class TestSecurityRepoProcessorNotFound:
    def _make_gh_with_not_found(self, fail_fragment: str):
        gh = MagicMock()

        def _getiter(url, *, url_vars=None):
            if fail_fragment in url:

                async def _fail():
                    raise GitHubNotFoundError("not found")
                    yield

                return _fail()
            if "dependabot" in url:
                return _aiter(*[{}] * 2)
            if "code-scanning" in url:
                return _aiter(*[{}] * 1)
            if "secret-scanning" in url:
                return _aiter(*[{}] * 1)
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        return gh

    @pytest.mark.anyio
    async def test_dependabot_not_found_sets_none(self):
        gh = self._make_gh_with_not_found("dependabot")
        processor, monitor = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["dependabot_alerts"] is None
        assert result.errors == []
        assert result.status == "success"

    @pytest.mark.anyio
    async def test_dependabot_not_found_emits_debug_event(self):
        gh = self._make_gh_with_not_found("dependabot")
        processor, monitor = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            await processor.run()
        debug_events = [
            e
            for e in monitor.events
            if e.severity == "debug" and "dependabot" in e.message.lower()
        ]
        assert len(debug_events) >= 1

    @pytest.mark.anyio
    async def test_code_scanning_not_found_sets_none(self):
        gh = self._make_gh_with_not_found("code-scanning")
        processor, monitor = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["code_scanning_alerts"] is None
        assert result.errors == []

    @pytest.mark.anyio
    async def test_secret_scanning_not_found_sets_none(self):
        gh = self._make_gh_with_not_found("secret-scanning")
        processor, monitor = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["secret_scanning_alerts"] is None
        assert result.errors == []


# ---------------------------------------------------------------------------
# GitHubApiError — partial result
# ---------------------------------------------------------------------------


class TestSecurityRepoProcessorApiError:
    def _make_gh_with_api_error(self, fail_fragment: str):
        gh = MagicMock()

        def _getiter(url, *, url_vars=None):
            if fail_fragment in url:

                async def _fail():
                    raise GitHubApiError("api error")
                    yield

                return _fail()
            if "dependabot" in url:
                return _aiter(*[{}] * 2)
            if "code-scanning" in url:
                return _aiter(*[{}] * 1)
            if "secret-scanning" in url:
                return _aiter(*[{}] * 1)
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        return gh

    @pytest.mark.anyio
    async def test_api_error_sets_none_and_partial(self):
        gh = self._make_gh_with_api_error("dependabot")
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.results["dependabot_alerts"] is None
        assert result.status == "partial"
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# FatalError propagation
# ---------------------------------------------------------------------------


class TestSecurityRepoProcessorFatalErrors:
    @pytest.mark.anyio
    async def test_primary_rate_limit_reraises(self):
        gh = MagicMock()

        async def _fail():
            raise GitHubPrimaryRateLimitError("rate limited")
            yield

        gh.getiter = MagicMock(return_value=_fail())
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            with pytest.raises(GitHubPrimaryRateLimitError):
                await processor.run()

    @pytest.mark.anyio
    async def test_secondary_rate_limit_reraises(self):
        gh = MagicMock()

        async def _fail():
            raise GitHubSecondaryRateLimitError("secondary rate limit")
            yield

        gh.getiter = MagicMock(return_value=_fail())
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            with pytest.raises(GitHubSecondaryRateLimitError):
                await processor.run()


# ---------------------------------------------------------------------------
# Unexpected exception containment
# ---------------------------------------------------------------------------


class TestSecurityRepoProcessorUnexpectedException:
    @pytest.mark.anyio
    async def test_unexpected_exception_sets_failed(self):
        gh = MagicMock()

        async def _fail():
            raise RuntimeError("something broke")
            yield

        gh.getiter = MagicMock(return_value=_fail())
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()
        assert result.status == "failed"
        assert len(result.errors) == 1

    @pytest.mark.anyio
    async def test_unexpected_exception_returns_result_not_raises(self):
        gh = MagicMock()

        async def _fail():
            raise RuntimeError("something broke")
            yield

        gh.getiter = MagicMock(return_value=_fail())
        processor, _ = _make_processor(gh)
        with patch("ghbot.processor.github_api_call", _passthrough):
            result = await processor.run()  # must not raise
        assert result is not None
