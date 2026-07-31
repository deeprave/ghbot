"""Tests for InfoRepoProcessor."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghbot.processor import (
    FeedbackEvent,
    InfoRepoProcessor,
    Monitor,
    RepoProcessor,
)


class RecordingMonitor:
    """Test stub that records all events sent to it."""

    def __init__(self) -> None:
        self.events: list[FeedbackEvent] = []

    async def send_event(self, event: FeedbackEvent) -> None:
        self.events.append(event)


class TestInfoRepoProcessorConstructor:
    """Tests for InfoRepoProcessor.__init__, owner, and repo properties."""

    def _make_gh(self) -> MagicMock:
        return MagicMock()

    def _make_monitor(self) -> RecordingMonitor:
        return RecordingMonitor()

    def test_empty_owner_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="owner"):
            InfoRepoProcessor(
                owner="",
                repo="widgets",
                gh=self._make_gh(),
                monitor=self._make_monitor(),
            )

    def test_empty_repo_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="repo"):
            InfoRepoProcessor(
                owner="acme", repo="", gh=self._make_gh(), monitor=self._make_monitor()
            )

    def test_valid_construction_stores_owner(self) -> None:
        gh = self._make_gh()
        monitor = self._make_monitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        assert processor.owner == "acme"

    def test_valid_construction_stores_repo(self) -> None:
        gh = self._make_gh()
        monitor = self._make_monitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        assert processor.repo == "widgets"

    def test_valid_construction_stores_gh(self) -> None:
        gh = self._make_gh()
        monitor = self._make_monitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        assert processor._gh is gh  # type: ignore[attr-defined]

    def test_valid_construction_stores_monitor(self) -> None:
        gh = self._make_gh()
        monitor = self._make_monitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        assert processor._monitor is monitor  # type: ignore[attr-defined]

    def test_owner_is_read_only(self) -> None:
        processor = InfoRepoProcessor(
            owner="acme",
            repo="widgets",
            gh=self._make_gh(),
            monitor=self._make_monitor(),
        )
        with pytest.raises(AttributeError):
            processor.owner = "other"  # type: ignore[misc]

    def test_repo_is_read_only(self) -> None:
        processor = InfoRepoProcessor(
            owner="acme",
            repo="widgets",
            gh=self._make_gh(),
            monitor=self._make_monitor(),
        )
        with pytest.raises(AttributeError):
            processor.repo = "other"  # type: ignore[misc]

    def test_isinstance_check_against_repo_processor(self) -> None:
        processor = InfoRepoProcessor(
            owner="acme",
            repo="widgets",
            gh=self._make_gh(),
            monitor=self._make_monitor(),
        )
        assert isinstance(processor, RepoProcessor)

    def test_isinstance_check_against_monitor_protocol_for_recording_monitor(
        self,
    ) -> None:
        monitor = RecordingMonitor()
        assert isinstance(monitor, Monitor)


# ---------------------------------------------------------------------------
# Helpers for TestInfoRepoProcessorRun
# ---------------------------------------------------------------------------


async def _aiter(*items):
    """Async generator helper — yields each item in turn."""
    for item in items:
        yield item


# Canned API responses used across all run() tests
_REPO_META = {
    "description": "A widget",
    "updated_at": "2024-01-01",
    "default_branch": "main",
}
_FILE_TREE = {"tree": [{"type": "blob"}, {"type": "blob"}, {"type": "tree"}]}
_LANGUAGES = {"Python": 1000, "JavaScript": 200}
_CONTRIBUTORS = [{"login": "alice"}, {"login": "bob"}]
_LATEST_RELEASE = {"tag_name": "v1.0.0"}
_OPEN_PRS = [{"number": 1}, {"number": 2}]
_OPEN_ISSUES = [
    {"number": 3},
    {"number": 4},
]  # no "pull_request" key → both are real issues
_SECURITY_ALERTS = [{"number": 1}]


def _make_gh_mock():
    """Build a MagicMock gh object with all required async methods pre-configured."""
    gh = MagicMock()

    # getitem returns different values depending on the URL
    async def _getitem(url, *, url_vars=None):
        if "/languages" in url:
            return _LANGUAGES
        if "/releases/latest" in url:
            return _LATEST_RELEASE
        if "/git/trees/" in url:
            return _FILE_TREE
        # Default: repo metadata
        return _REPO_META

    gh.getitem = AsyncMock(side_effect=_getitem)

    # getiter returns an async generator depending on the URL
    def _getiter(url, *, url_vars=None):
        if "/contributors" in url:
            return _aiter(*_CONTRIBUTORS)
        if "/pulls" in url:
            return _aiter(*_OPEN_PRS)
        if "/issues" in url:
            return _aiter(*_OPEN_ISSUES)
        if "/vulnerability-alerts" in url:
            return _aiter(*_SECURITY_ALERTS)
        return _aiter()

    gh.getiter = MagicMock(side_effect=_getiter)
    return gh


@asynccontextmanager
async def _passthrough_github_api_call(gh):
    """Replacement for github_api_call that does nothing — just yields."""
    yield


class TestInfoRepoProcessorRun:
    """Tests for InfoRepoProcessor.run() — happy path with mocked GitHub API."""

    def _make_processor(self):
        gh = _make_gh_mock()
        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        return processor, monitor

    @pytest.mark.anyio
    async def test_run_sends_start_progress_event(self) -> None:
        processor, monitor = self._make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()
        first = monitor.events[0]
        assert first.type == "progress"
        assert first.severity == "info"
        assert "start" in first.message.lower() or "processing" in first.message.lower()

    @pytest.mark.anyio
    async def test_run_sends_finish_progress_event(self) -> None:
        processor, monitor = self._make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()
        last = monitor.events[-1]
        assert last.type == "progress"
        assert last.severity == "debug"
        assert "finish" in last.message.lower() or "processing" in last.message.lower()

    @pytest.mark.anyio
    async def test_run_sends_per_step_progress_events(self) -> None:
        processor, monitor = self._make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()
        # Exclude the first (start) and last (finish) events
        middle_events = monitor.events[1:-1]
        # There should be exactly 8 per-step progress events (one per data-fetching step)
        step_progress = [
            e for e in middle_events if e.type == "progress" and e.severity == "debug"
        ]
        assert len(step_progress) == 8

    @pytest.mark.anyio
    async def test_run_returns_success_status(self) -> None:
        processor, _monitor = self._make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert result.status == "success"

    @pytest.mark.anyio
    async def test_run_returns_correct_owner_and_repo(self) -> None:
        processor, _monitor = self._make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert result.owner == "acme"
        assert result.repo == "widgets"

    @pytest.mark.anyio
    async def test_run_results_contains_all_9_keys(self) -> None:
        processor, _monitor = self._make_processor()
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        expected_keys = {
            "description",
            "updated_at",
            "file_count",
            "languages",
            "contributors",
            "latest_release",
            "open_pull_requests",
            "open_issues",
            "security_alerts",
        }
        assert expected_keys.issubset(result.results.keys())


# ---------------------------------------------------------------------------
# Helpers shared by error-handling tests
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _raising_github_api_call(exc):
    """Context manager that raises `exc` immediately — simulates API failure."""
    raise exc
    yield


def _make_failing_gh_mock(fail_url_fragment: str, exc: Exception):
    """
    Build a gh mock where calls to URLs containing `fail_url_fragment` raise `exc`.
    All other calls succeed with canned responses.
    """
    gh = MagicMock()

    async def _getitem(url, *, url_vars=None):
        if fail_url_fragment in url:
            raise exc
        if "/languages" in url:
            return _LANGUAGES
        if "/releases/latest" in url:
            return _LATEST_RELEASE
        if "/git/trees/" in url:
            return _FILE_TREE
        return _REPO_META

    gh.getitem = AsyncMock(side_effect=_getitem)

    def _getiter(url, *, url_vars=None):
        if fail_url_fragment in url:

            async def _failing():
                raise exc
                yield

            return _failing()
        if "/contributors" in url:
            return _aiter(*_CONTRIBUTORS)
        if "/pulls" in url:
            return _aiter(*_OPEN_PRS)
        if "/issues" in url:
            return _aiter(*_OPEN_ISSUES)
        if "/vulnerability-alerts" in url:
            return _aiter(*_SECURITY_ALERTS)
        return _aiter()

    gh.getiter = MagicMock(side_effect=_getiter)
    return gh


# ---------------------------------------------------------------------------
# 8.1 — Per-step GitHubApiError resilience
# ---------------------------------------------------------------------------


class TestInfoRepoProcessorGitHubApiErrorResilience:
    """Tests for per-step GitHubApiError handling (subtask 8.1)."""

    def _make_processor_with_failing_step(self, fail_url_fragment: str, exc: Exception):
        from ghbot.errors import GitHubApiError as _GitHubApiError  # noqa: F401

        gh = _make_failing_gh_mock(fail_url_fragment, exc)
        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        return processor, monitor

    @pytest.mark.anyio
    async def test_single_step_failure_sets_status_partial(self) -> None:
        """A GitHubApiError on one step → status 'partial'."""
        from ghbot.errors import GitHubApiError

        processor, _monitor = self._make_processor_with_failing_step(
            "/git/trees/", GitHubApiError("tree fetch failed")
        )
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert result.status == "partial"

    @pytest.mark.anyio
    async def test_single_step_failure_records_error(self) -> None:
        """A GitHubApiError on one step → error message in result.errors."""
        from ghbot.errors import GitHubApiError

        processor, _monitor = self._make_processor_with_failing_step(
            "/git/trees/", GitHubApiError("tree fetch failed")
        )
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert len(result.errors) == 1
        assert (
            "tree fetch failed" in result.errors[0] or "file count" in result.errors[0]
        )

    @pytest.mark.anyio
    async def test_single_step_failure_sets_default_value(self) -> None:
        """A GitHubApiError on file_count step → file_count defaults to 0."""
        from ghbot.errors import GitHubApiError

        processor, _monitor = self._make_processor_with_failing_step(
            "/git/trees/", GitHubApiError("tree fetch failed")
        )
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert result.results["file_count"] == 0

    @pytest.mark.anyio
    async def test_single_step_failure_other_steps_have_valid_data(self) -> None:
        """A GitHubApiError on file_count step → other steps still populated."""
        from ghbot.errors import GitHubApiError

        processor, _monitor = self._make_processor_with_failing_step(
            "/git/trees/", GitHubApiError("tree fetch failed")
        )
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        # Other steps should have valid data
        assert result.results["description"] == "A widget"
        assert result.results["languages"] == _LANGUAGES
        assert result.results["contributors"] == _CONTRIBUTORS
        assert result.results["latest_release"] == _LATEST_RELEASE

    @pytest.mark.anyio
    async def test_single_step_failure_sends_error_event(self) -> None:
        """A GitHubApiError on one step → monitor receives an error-severity event."""
        from ghbot.errors import GitHubApiError

        processor, monitor = self._make_processor_with_failing_step(
            "/git/trees/", GitHubApiError("tree fetch failed")
        )
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()
        error_events = [e for e in monitor.events if e.severity == "error"]
        assert len(error_events) >= 1

    @pytest.mark.anyio
    async def test_multiple_step_failures_status_partial(self) -> None:
        """Multiple GitHubApiErrors → status 'partial' with multiple errors."""
        from ghbot.errors import GitHubApiError

        gh = MagicMock()

        async def _getitem(url, *, url_vars=None):
            if "/git/trees/" in url:
                raise GitHubApiError("tree failed")
            if "/languages" in url:
                raise GitHubApiError("languages failed")
            if "/releases/latest" in url:
                return _LATEST_RELEASE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)

        def _getiter(url, *, url_vars=None):
            if "/contributors" in url:
                return _aiter(*_CONTRIBUTORS)
            if "/pulls" in url:
                return _aiter(*_OPEN_PRS)
            if "/issues" in url:
                return _aiter(*_OPEN_ISSUES)
            if "/vulnerability-alerts" in url:
                return _aiter(*_SECURITY_ALERTS)
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.status == "partial"
        assert len(result.errors) == 2

    @pytest.mark.anyio
    async def test_multiple_step_failures_records_all_errors(self) -> None:
        """Multiple GitHubApiErrors → all error messages recorded."""
        from ghbot.errors import GitHubApiError

        gh = MagicMock()

        async def _getitem(url, *, url_vars=None):
            if "/git/trees/" in url:
                raise GitHubApiError("tree failed")
            if "/languages" in url:
                raise GitHubApiError("languages failed")
            if "/releases/latest" in url:
                return _LATEST_RELEASE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        gh.getiter = MagicMock(side_effect=lambda url, *, url_vars=None: _aiter())

        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        # Both errors should be recorded
        combined = " ".join(result.errors)
        assert "tree failed" in combined or "file count" in combined
        assert "languages failed" in combined or "languages" in combined


# ---------------------------------------------------------------------------
# 8.2 — Edge cases: no releases, empty languages, security alerts 403
# ---------------------------------------------------------------------------


class TestInfoRepoProcessorEdgeCases:
    """Tests for edge cases in specific fetch methods (subtask 8.2)."""

    def _make_processor(self, gh):
        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        return processor, monitor

    @pytest.mark.anyio
    async def test_no_releases_sets_latest_release_to_none(self) -> None:
        """GitHubNotFoundError on releases → latest_release is None."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/releases/latest" in url:
                raise GitHubNotFoundError("not found")
            if "/languages" in url:
                return _LANGUAGES
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, _monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.results["latest_release"] is None

    @pytest.mark.anyio
    async def test_no_releases_sends_warning_event(self) -> None:
        """GitHubNotFoundError on releases → debug event sent."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/releases/latest" in url:
                raise GitHubNotFoundError("not found")
            if "/languages" in url:
                return _LANGUAGES
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()

        fetch_debug_events = [
            e for e in monitor.events if e.severity == "debug" and e.type == "fetch"
        ]
        assert any("release" in e.message.lower() for e in fetch_debug_events)

    @pytest.mark.anyio
    async def test_no_releases_does_not_add_to_errors(self) -> None:
        """GitHubNotFoundError on releases → no error recorded (it's a warning, not an error)."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/releases/latest" in url:
                raise GitHubNotFoundError("not found")
            if "/languages" in url:
                return _LANGUAGES
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, _monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.errors == []
        assert result.status == "success"

    @pytest.mark.anyio
    async def test_empty_languages_sets_languages_to_empty_dict(self) -> None:
        """Empty response from languages endpoint → languages is {}."""
        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/languages" in url:
                return {}  # empty response
            if "/releases/latest" in url:
                return _LATEST_RELEASE
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, _monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.results["languages"] == {}

    @pytest.mark.anyio
    async def test_empty_languages_sends_warning_event(self) -> None:
        """Empty response from languages endpoint → debug event sent."""
        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/languages" in url:
                return {}
            if "/releases/latest" in url:
                return _LATEST_RELEASE
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()

        fetch_debug_events = [
            e for e in monitor.events if e.severity == "debug" and e.type == "fetch"
        ]
        assert any("language" in e.message.lower() for e in fetch_debug_events)

    @pytest.mark.anyio
    async def test_languages_not_found_sends_debug_event(self) -> None:
        """GitHubNotFoundError on languages endpoint → debug event sent."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/languages" in url:
                raise GitHubNotFoundError("not found")
            if "/releases/latest" in url:
                return _LATEST_RELEASE
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()

        fetch_debug_events = [
            e for e in monitor.events if e.severity == "debug" and e.type == "fetch"
        ]
        assert any("language" in e.message.lower() for e in fetch_debug_events)

    @pytest.mark.anyio
    async def test_empty_languages_does_not_add_to_errors(self) -> None:
        """Empty languages response → no error recorded (it's a warning)."""
        gh = _make_gh_mock()

        async def _getitem(url, *, url_vars=None):
            if "/languages" in url:
                return {}
            if "/releases/latest" in url:
                return _LATEST_RELEASE
            if "/git/trees/" in url:
                return _FILE_TREE
            return _REPO_META

        gh.getitem = AsyncMock(side_effect=_getitem)
        processor, _monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.errors == []
        assert result.status == "success"

    @pytest.mark.anyio
    async def test_security_alerts_403_sets_empty_list(self) -> None:
        """GitHubNotFoundError (403) on security alerts → security_alerts is []."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        def _getiter(url, *, url_vars=None):
            if "/vulnerability-alerts" in url:

                async def _failing():
                    raise GitHubNotFoundError("403 forbidden")
                    yield

                return _failing()
            if "/contributors" in url:
                return _aiter(*_CONTRIBUTORS)
            if "/pulls" in url:
                return _aiter(*_OPEN_PRS)
            if "/issues" in url:
                return _aiter(*_OPEN_ISSUES)
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        processor, _monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.results["security_alerts"] == []

    @pytest.mark.anyio
    async def test_security_alerts_403_sends_warning_event(self) -> None:
        """GitHubNotFoundError (403) on security alerts → debug event sent."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        def _getiter(url, *, url_vars=None):
            if "/vulnerability-alerts" in url:

                async def _failing():
                    raise GitHubNotFoundError("403 forbidden")
                    yield

                return _failing()
            if "/contributors" in url:
                return _aiter(*_CONTRIBUTORS)
            if "/pulls" in url:
                return _aiter(*_OPEN_PRS)
            if "/issues" in url:
                return _aiter(*_OPEN_ISSUES)
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        processor, monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()

        fetch_debug_events = [
            e for e in monitor.events if e.severity == "debug" and e.type == "fetch"
        ]
        assert any(
            "security" in e.message.lower() or "alert" in e.message.lower()
            for e in fetch_debug_events
        )

    @pytest.mark.anyio
    async def test_security_alerts_403_does_not_add_to_errors(self) -> None:
        """GitHubNotFoundError (403) on security alerts → no error recorded (it's a warning)."""
        from ghbot.errors import GitHubNotFoundError

        gh = _make_gh_mock()

        def _getiter(url, *, url_vars=None):
            if "/vulnerability-alerts" in url:

                async def _failing():
                    raise GitHubNotFoundError("403 forbidden")
                    yield

                return _failing()
            if "/contributors" in url:
                return _aiter(*_CONTRIBUTORS)
            if "/pulls" in url:
                return _aiter(*_OPEN_PRS)
            if "/issues" in url:
                return _aiter(*_OPEN_ISSUES)
            return _aiter()

        gh.getiter = MagicMock(side_effect=_getiter)
        processor, _monitor = self._make_processor(gh)

        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()

        assert result.errors == []
        assert result.status == "success"


# ---------------------------------------------------------------------------
# 8.3 — Unexpected exception containment
# ---------------------------------------------------------------------------


class TestInfoRepoProcessorUnexpectedExceptionContainment:
    """Tests for unexpected exception handling in run() (subtask 8.3)."""

    def _make_processor_raising(self, exc: Exception):
        """Build a processor whose first API call raises an unexpected exception."""
        gh = MagicMock()

        async def _getitem(url, *, url_vars=None):
            raise exc

        gh.getitem = AsyncMock(side_effect=_getitem)
        gh.getiter = MagicMock(side_effect=lambda url, *, url_vars=None: _aiter())
        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        return processor, monitor

    @pytest.mark.anyio
    async def test_runtime_error_sets_status_failed(self) -> None:
        """RuntimeError during processing → status 'failed'."""
        processor, _monitor = self._make_processor_raising(RuntimeError("boom"))
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert result.status == "failed"

    @pytest.mark.anyio
    async def test_runtime_error_records_error(self) -> None:
        """RuntimeError during processing → error recorded in result.errors."""
        processor, _monitor = self._make_processor_raising(RuntimeError("boom"))
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert len(result.errors) >= 1
        assert "boom" in result.errors[0]

    @pytest.mark.anyio
    async def test_runtime_error_returns_repo_result_not_raised(self) -> None:
        """RuntimeError during processing → RepoResult returned, not raised."""
        from ghbot.processor import RepoResult

        processor, _monitor = self._make_processor_raising(RuntimeError("boom"))
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert isinstance(result, RepoResult)

    @pytest.mark.anyio
    async def test_runtime_error_sends_error_event(self) -> None:
        """RuntimeError during processing → error-severity event sent to monitor."""
        processor, monitor = self._make_processor_raising(RuntimeError("boom"))
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()
        error_events = [e for e in monitor.events if e.severity == "error"]
        assert len(error_events) >= 1

    @pytest.mark.anyio
    async def test_value_error_sets_status_failed(self) -> None:
        """ValueError during processing → status 'failed'."""
        processor, _monitor = self._make_processor_raising(ValueError("bad value"))
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            result = await processor.run()
        assert result.status == "failed"

    @pytest.mark.anyio
    async def test_unexpected_exception_still_sends_finish_event(self) -> None:
        """Unexpected exception → finish progress event still sent."""
        processor, monitor = self._make_processor_raising(RuntimeError("boom"))
        with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
            await processor.run()
        last = monitor.events[-1]
        assert last.type == "progress"
        assert "finish" in last.message.lower() or "processing" in last.message.lower()


# ---------------------------------------------------------------------------
# 8.4 — FatalError propagation
# ---------------------------------------------------------------------------


class TestInfoRepoProcessorFatalErrorPropagation:
    """Tests for FatalError re-raise from run() (subtask 8.4)."""

    def _make_processor_raising(self, exc: Exception):
        """Build a processor whose first API call raises the given exception."""
        gh = MagicMock()

        async def _getitem(url, *, url_vars=None):
            raise exc

        gh.getitem = AsyncMock(side_effect=_getitem)
        gh.getiter = MagicMock(side_effect=lambda url, *, url_vars=None: _aiter())
        monitor = RecordingMonitor()
        processor = InfoRepoProcessor(
            owner="acme", repo="widgets", gh=gh, monitor=monitor
        )
        return processor, monitor

    @pytest.mark.anyio
    async def test_primary_rate_limit_error_is_reraised(self) -> None:
        """GitHubPrimaryRateLimitError raised during a step → re-raised from run()."""
        from ghbot.errors import GitHubPrimaryRateLimitError

        processor, _monitor = self._make_processor_raising(
            GitHubPrimaryRateLimitError("rate limit exceeded")
        )
        with (
            patch("ghbot.processor.github_api_call", _passthrough_github_api_call),
            pytest.raises(GitHubPrimaryRateLimitError),
        ):
            await processor.run()

    @pytest.mark.anyio
    async def test_secondary_rate_limit_error_is_reraised(self) -> None:
        """GitHubSecondaryRateLimitError raised during a step → re-raised from run()."""
        from ghbot.errors import GitHubSecondaryRateLimitError

        processor, _monitor = self._make_processor_raising(
            GitHubSecondaryRateLimitError("secondary rate limit")
        )
        with (
            patch("ghbot.processor.github_api_call", _passthrough_github_api_call),
            pytest.raises(GitHubSecondaryRateLimitError),
        ):
            await processor.run()

    @pytest.mark.anyio
    async def test_primary_rate_limit_not_caught_as_unexpected(self) -> None:
        """GitHubPrimaryRateLimitError must NOT be swallowed as an unexpected exception."""
        from ghbot.errors import GitHubPrimaryRateLimitError

        processor, _monitor = self._make_processor_raising(
            GitHubPrimaryRateLimitError("rate limit exceeded")
        )
        with (
            patch("ghbot.processor.github_api_call", _passthrough_github_api_call),
            pytest.raises(GitHubPrimaryRateLimitError),
        ):
            await processor.run()
        # Status should NOT be "failed" — the exception escaped
        # (We can't check result.status here since run() raised, but the test
        # confirms the exception propagated rather than being swallowed.)

    @pytest.mark.anyio
    async def test_secondary_rate_limit_not_caught_as_unexpected(self) -> None:
        """GitHubSecondaryRateLimitError must NOT be swallowed as an unexpected exception."""
        from ghbot.errors import GitHubSecondaryRateLimitError

        processor, _monitor = self._make_processor_raising(
            GitHubSecondaryRateLimitError("secondary rate limit")
        )
        with (
            patch("ghbot.processor.github_api_call", _passthrough_github_api_call),
            pytest.raises(GitHubSecondaryRateLimitError),
        ):
            await processor.run()
