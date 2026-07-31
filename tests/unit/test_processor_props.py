"""Property-based tests for processor correctness properties."""

import asyncio
import logging
import logging.handlers
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch as mock_patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from ghbot.errors import (
    GitHubApiError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.processor import FeedbackEvent, InfoRepoProcessor, LoggingMonitor

SEVERITY_TO_LEVEL = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

# ---------------------------------------------------------------------------
# DATA_POINT_STEPS — one entry per _fetch_* method in InfoRepoProcessor.
#
# Each entry is a dict with:
#   url_fragment  — substring present in the URL that step calls
#   result_key    — key written into RepoResult.results by that step
#   default       — the value set when the step fails with GitHubApiError
#   uses_getiter  — True if the step uses gh.getiter (not gh.getitem)
# ---------------------------------------------------------------------------

DATA_POINT_STEPS = [
    {
        "url_fragment": "/repos/{owner}/{repo}",  # repo metadata (no other fragment matches)
        "result_key": "description",
        "default": None,
        "uses_getiter": False,
        "is_metadata": True,  # also sets updated_at and _default_branch
    },
    {
        "url_fragment": "/git/trees/",
        "result_key": "file_count",
        "default": 0,
        "uses_getiter": False,
        "is_metadata": False,
    },
    {
        "url_fragment": "/languages",
        "result_key": "languages",
        "default": {},
        "uses_getiter": False,
        "is_metadata": False,
    },
    {
        "url_fragment": "/contributors",
        "result_key": "contributors",
        "default": [],
        "uses_getiter": True,
        "is_metadata": False,
    },
    {
        "url_fragment": "/releases/latest",
        "result_key": "latest_release",
        "default": None,
        "uses_getiter": False,
        "is_metadata": False,
    },
    {
        "url_fragment": "/pulls",
        "result_key": "open_pull_requests",
        "default": 0,
        "uses_getiter": True,
        "is_metadata": False,
    },
    {
        "url_fragment": "/issues",
        "result_key": "open_issues",
        "default": 0,
        "uses_getiter": True,
        "is_metadata": False,
    },
    {
        "url_fragment": "/vulnerability-alerts",
        "result_key": "security_alerts",
        "default": [],
        "uses_getiter": True,
        "is_metadata": False,
    },
]


# Feature: repo-processor, Property 1: Owner/repo construction round-trip
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
)
def test_owner_repo_roundtrip(owner: str, repo: str) -> None:
    """For any non-empty owner and repo, InfoRepoProcessor stores and returns them exactly."""
    gh = AsyncMock()
    monitor = AsyncMock()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    assert processor.owner == owner
    assert processor.repo == repo


# Feature: repo-processor, Property 2: Severity-to-log-level mapping
@settings(max_examples=100)
@given(
    severity=st.sampled_from(["debug", "info", "warning", "error"]),
    event_type=st.text(),
    message=st.text(),
)
def test_severity_to_log_level(
    severity: str,
    event_type: str,
    message: str,
) -> None:
    """For any known severity, LoggingMonitor.send_event logs at the corresponding level."""
    owner = "test-owner"
    repo = "test-repo"
    logger_name = f"ghbot.processor.{owner}/{repo}"
    monitor = LoggingMonitor(owner=owner, repo=repo)

    logger = logging.getLogger(logger_name)
    handler = logging.handlers.MemoryHandler(capacity=10)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        event = FeedbackEvent(type=event_type, severity=severity, message=message)
        asyncio.run(monitor.send_event(event))

        assert len(handler.buffer) == 1
        record = handler.buffer[0]
        assert record.levelno == SEVERITY_TO_LEVEL[severity]
    finally:
        handler.buffer.clear()
        logger.removeHandler(handler)


# Feature: repo-processor, Property 3: Log message contains owner and repo context
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
    event=st.builds(
        FeedbackEvent,
        type=st.text(),
        severity=st.text(),
        message=st.text(),
    ),
)
def test_log_message_contains_owner_and_repo(
    owner: str,
    repo: str,
    event: FeedbackEvent,
) -> None:
    """For any owner, repo, and FeedbackEvent, the log message contains both owner and repo."""
    logger_name = f"ghbot.processor.{owner}/{repo}"
    monitor = LoggingMonitor(owner=owner, repo=repo)

    logger = logging.getLogger(logger_name)
    handler = logging.handlers.MemoryHandler(capacity=10)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    try:
        asyncio.run(monitor.send_event(event))

        assert len(handler.buffer) == 1
        record = handler.buffer[0]
        assert owner in record.message
        assert repo in record.message
    finally:
        handler.buffer.clear()
        logger.removeHandler(handler)


# ---------------------------------------------------------------------------
# Helpers shared by property tests that exercise InfoRepoProcessor.run()
# ---------------------------------------------------------------------------


async def _aiter_prop(*items):
    """Async generator that yields each item in turn."""
    for item in items:
        yield item


def _make_succeeding_gh() -> MagicMock:
    """Return a gh mock where every API call succeeds with minimal canned data."""
    gh = MagicMock()

    async def _getitem(url, *, url_vars=None):
        if "/languages" in url:
            return {"Python": 100}
        if "/releases/latest" in url:
            return {"tag_name": "v1.0.0"}
        if "/git/trees/" in url:
            return {"tree": [{"type": "blob"}]}
        # Default: repo metadata
        return {
            "description": "desc",
            "updated_at": "2024-01-01",
            "default_branch": "main",
        }

    gh.getitem = AsyncMock(side_effect=_getitem)

    def _getiter(url, *, url_vars=None):
        if "/contributors" in url:
            return _aiter_prop({"login": "alice"})
        if "/pulls" in url:
            return _aiter_prop({"number": 1})
        if "/issues" in url:
            return _aiter_prop({"number": 2})
        if "/vulnerability-alerts" in url:
            return _aiter_prop({"number": 3})
        return _aiter_prop()

    gh.getiter = MagicMock(side_effect=_getiter)
    return gh


@asynccontextmanager
async def _noop_github_api_call(gh):
    """Passthrough replacement for github_api_call — just yields."""
    yield


# Feature: repo-processor, Property 4: Successful run produces correct RepoResult fields
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
)
def test_successful_run_fields(owner: str, repo: str) -> None:
    """For any non-empty owner/repo, a fully-mocked successful run returns the correct fields."""
    gh = _make_succeeding_gh()
    monitor = AsyncMock()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with mock_patch("ghbot.processor.github_api_call", _noop_github_api_call):
        result = asyncio.run(processor.run())

    assert result.owner == owner
    assert result.repo == repo
    assert result.status == "success"


# Feature: repo-processor, Property 8: Results dict completeness
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
)
def test_results_completeness(owner: str, repo: str) -> None:
    """For any non-empty owner/repo, a fully-mocked successful run populates all 9 result keys."""
    gh = _make_succeeding_gh()
    monitor = AsyncMock()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with mock_patch("ghbot.processor.github_api_call", _noop_github_api_call):
        result = asyncio.run(processor.run())

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


def _make_gh_with_one_failing_step(failing_step: dict) -> MagicMock:
    """
    Return a gh mock where the step identified by `failing_step` raises a plain
    GitHubApiError, and every other step succeeds with minimal canned data.

    We use a plain GitHubApiError (not a rate-limit subclass) so that the
    per-step catch in each _fetch_* method handles it rather than the outer
    FatalError re-raise.
    """
    exc = GitHubApiError("injected step failure")
    fail_fragment = failing_step["url_fragment"]
    fail_uses_getiter = failing_step["uses_getiter"]
    fail_is_metadata = failing_step.get("is_metadata", False)

    gh = MagicMock()

    async def _getitem(url, *, url_vars=None):
        # The metadata step is identified by the absence of any more-specific fragment.
        # We match it only when fail_is_metadata is True and no other fragment matches.
        if fail_is_metadata:
            # Only fail on the bare repo metadata call (not languages, trees, releases)
            if (
                "/languages" not in url
                and "/git/trees/" not in url
                and "/releases/latest" not in url
            ):
                raise exc
        elif fail_fragment in url and not fail_uses_getiter:
            raise exc

        # Successful responses for all other getitem calls
        if "/languages" in url:
            return {"Python": 100}
        if "/releases/latest" in url:
            return {"tag_name": "v1.0.0"}
        if "/git/trees/" in url:
            return {"tree": [{"type": "blob"}]}
        # Default: repo metadata
        return {
            "description": "desc",
            "updated_at": "2024-01-01",
            "default_branch": "main",
        }

    gh.getitem = AsyncMock(side_effect=_getitem)

    def _getiter(url, *, url_vars=None):
        if fail_uses_getiter and fail_fragment in url:

            async def _failing():
                raise exc
                yield

            return _failing()
        if "/contributors" in url:
            return _aiter_prop({"login": "alice"})
        if "/pulls" in url:
            return _aiter_prop({"number": 1})
        if "/issues" in url:
            return _aiter_prop({"number": 2})
        if "/vulnerability-alerts" in url:
            return _aiter_prop({"number": 3})
        return _aiter_prop()

    gh.getiter = MagicMock(side_effect=_getiter)
    return gh


# Feature: repo-processor, Property 5: Per-step error resilience
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
    failing_step=st.sampled_from(DATA_POINT_STEPS),
)
def test_per_step_error_resilience(
    owner: str,
    repo: str,
    failing_step: dict,
) -> None:
    """For any single step that raises GitHubApiError, run() returns status 'partial',
    records the error, sets the default for the failed step, and populates all other steps.
    """
    gh = _make_gh_with_one_failing_step(failing_step)
    monitor = AsyncMock()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with mock_patch("ghbot.processor.github_api_call", _noop_github_api_call):
        result = asyncio.run(processor.run())

    # Status must be "partial" — not "success" or "failed"
    assert result.status == "partial", (
        f"Expected 'partial' but got '{result.status}' for step {failing_step['result_key']!r}"
    )

    # At least one error must be recorded
    assert len(result.errors) >= 1, (
        f"Expected at least one error for step {failing_step['result_key']!r}, got none"
    )

    # The failed step's result key must be set to its default value
    result_key = failing_step["result_key"]
    expected_default = failing_step["default"]
    assert result.results.get(result_key) == expected_default, (
        f"Expected default {expected_default!r} for key {result_key!r}, "
        f"got {result.results.get(result_key)!r}"
    )

    # All other (non-failing) steps must have valid (non-default) data.
    # We check that every other result key is present in the results dict.
    all_keys = {step["result_key"] for step in DATA_POINT_STEPS}
    other_keys = all_keys - {result_key}
    # Metadata step also sets updated_at; include it in the check
    if failing_step.get("is_metadata"):
        other_keys -= {"updated_at"}  # also set by the same step
    for key in other_keys:
        assert key in result.results, (
            f"Expected key {key!r} to be present in results when step "
            f"{result_key!r} fails, but it was missing"
        )


# Feature: repo-processor, Property 6: Unexpected exception containment
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
    exc_type=st.sampled_from([RuntimeError, ValueError, TypeError, KeyError]),
)
def test_unexpected_exception_containment(
    owner: str,
    repo: str,
    exc_type: type,
) -> None:
    """For any unexpected exception raised during a processing step, run() catches it,
    sets status to 'failed', records the error, and returns a RepoResult without propagating.

    Validates: Requirements 4.6, 6.2
    """
    from ghbot.processor import RepoResult

    exc = exc_type("injected unexpected error")

    gh = MagicMock()

    async def _getitem(url, *, url_vars=None):
        raise exc

    gh.getitem = AsyncMock(side_effect=_getitem)
    gh.getiter = MagicMock(side_effect=lambda url, *, url_vars=None: _aiter_prop())

    monitor = AsyncMock()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with mock_patch("ghbot.processor.github_api_call", _noop_github_api_call):
        result = asyncio.run(processor.run())

    # Must return a RepoResult — not raise
    assert isinstance(result, RepoResult), (
        f"Expected RepoResult to be returned, but got {type(result)!r}"
    )

    # Status must be "failed"
    assert result.status == "failed", (
        f"Expected status 'failed' but got {result.status!r} for {exc_type.__name__}"
    )

    # At least one error must be recorded
    assert len(result.errors) >= 1, (
        f"Expected at least one error recorded for {exc_type.__name__}, got none"
    )


# Feature: repo-processor, Property 7: FatalError propagation
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
    exc_type=st.sampled_from(
        [GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError]
    ),
)
def test_fatal_error_propagation(
    owner: str,
    repo: str,
    exc_type: type,
) -> None:
    """For any FatalError subclass raised during a processing step, run() re-raises it
    so that the TaskPool can handle it with its abort/retry logic.

    Validates: Requirements 6.3
    """
    exc = exc_type("injected fatal error")

    gh = MagicMock()

    async def _getitem(url, *, url_vars=None):
        raise exc

    gh.getitem = AsyncMock(side_effect=_getitem)
    gh.getiter = MagicMock(side_effect=lambda url, *, url_vars=None: _aiter_prop())

    monitor = AsyncMock()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with (
        mock_patch("ghbot.processor.github_api_call", _noop_github_api_call),
        pytest.raises(exc_type),
    ):
        asyncio.run(processor.run())


# Feature: output-verbosity, Property 3: Run lifecycle events have correct severities
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
)
def test_run_lifecycle_event_severities(owner: str, repo: str) -> None:
    """For any non-empty owner/repo, the first FeedbackEvent emitted by run() has
    type='progress' and severity='info', and the last has type='progress' and severity='debug'.

    Validates: Requirements 3.1, 3.2
    """

    class RecordingMonitor:
        def __init__(self):
            self.events: list[FeedbackEvent] = []

        async def send_event(self, event: FeedbackEvent) -> None:
            self.events.append(event)

    gh = _make_succeeding_gh()
    monitor = RecordingMonitor()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with mock_patch("ghbot.processor.github_api_call", _noop_github_api_call):
        asyncio.run(processor.run())

    assert len(monitor.events) >= 2, (
        f"Expected at least 2 events but got {len(monitor.events)}: {monitor.events!r}"
    )

    first = monitor.events[0]
    assert first.type == "progress", (
        f"Expected first event type='progress' but got {first.type!r}"
    )
    assert first.severity == "info", (
        f"Expected first event severity='info' but got {first.severity!r}"
    )

    last = monitor.events[-1]
    assert last.type == "progress", (
        f"Expected last event type='progress' but got {last.type!r}"
    )
    assert last.severity == "debug", (
        f"Expected last event severity='debug' but got {last.severity!r}"
    )


# Feature: output-verbosity, Property 1: Empty-state conditions emit debug-severity events
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
    empty_state=st.sampled_from(
        [
            "release_not_found",
            "languages_empty",
            "languages_not_found",
            "security_not_found",
        ]
    ),
)
def test_empty_state_events_are_debug(owner: str, repo: str, empty_state: str) -> None:
    """For any empty-state condition, InfoRepoProcessor emits a FeedbackEvent with
    severity='debug' and type='fetch'.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    from ghbot.errors import GitHubNotFoundError

    # Recording monitor that collects all FeedbackEvent objects
    class RecordingMonitor:
        def __init__(self):
            self.events: list[FeedbackEvent] = []

        async def send_event(self, event: FeedbackEvent) -> None:
            self.events.append(event)

    gh = _make_succeeding_gh()

    if empty_state == "release_not_found":
        # Override getitem so /releases/latest raises GitHubNotFoundError
        original_getitem = gh.getitem.side_effect

        async def _getitem_no_release(url, *, url_vars=None):
            if "/releases/latest" in url:
                raise GitHubNotFoundError("not found")
            return await original_getitem(url, url_vars=url_vars)

        gh.getitem = AsyncMock(side_effect=_getitem_no_release)

    elif empty_state == "languages_empty":
        # Override getitem so /languages returns {}
        original_getitem = gh.getitem.side_effect

        async def _getitem_empty_languages(url, *, url_vars=None):
            if "/languages" in url:
                return {}
            return await original_getitem(url, url_vars=url_vars)

        gh.getitem = AsyncMock(side_effect=_getitem_empty_languages)

    elif empty_state == "languages_not_found":
        # Override getitem so /languages raises GitHubNotFoundError
        original_getitem = gh.getitem.side_effect

        async def _getitem_no_languages(url, *, url_vars=None):
            if "/languages" in url:
                raise GitHubNotFoundError("not found")
            return await original_getitem(url, url_vars=url_vars)

        gh.getitem = AsyncMock(side_effect=_getitem_no_languages)

    elif empty_state == "security_not_found":
        # Override getiter so /vulnerability-alerts raises GitHubNotFoundError
        original_getiter = gh.getiter.side_effect

        def _getiter_no_security(url, *, url_vars=None):
            if "/vulnerability-alerts" in url:

                async def _failing_iter():
                    raise GitHubNotFoundError("not found")
                    yield

                return _failing_iter()
            return original_getiter(url, url_vars=url_vars)

        gh.getiter = MagicMock(side_effect=_getiter_no_security)

    monitor = RecordingMonitor()
    processor = InfoRepoProcessor(owner=owner, repo=repo, gh=gh, monitor=monitor)

    with mock_patch("ghbot.processor.github_api_call", _noop_github_api_call):
        asyncio.run(processor.run())

    # Assert at least one event has severity='debug' AND type='fetch'
    # (type='fetch' distinguishes empty-state events from per-step progress events)
    debug_fetch_events = [
        e for e in monitor.events if e.severity == "debug" and e.type == "fetch"
    ]
    assert len(debug_fetch_events) >= 1, (
        f"Expected at least one FeedbackEvent with severity='debug' and type='fetch' "
        f"for empty_state={empty_state!r}, but got events: {monitor.events!r}"
    )


# Feature: output-verbosity, Property 4: LoggingMonitor never routes to the requests logger
@settings(max_examples=100)
@given(
    event=st.builds(
        FeedbackEvent,
        type=st.text(),
        severity=st.text(),
        message=st.text(),
    ),
)
def test_logging_monitor_never_uses_requests_logger(event: FeedbackEvent) -> None:
    """For any FeedbackEvent, LoggingMonitor.send_event never routes to the requests logger.

    Validates: Requirement 4.5
    """
    requests_logger = logging.getLogger("ghbot.requests")
    handler = logging.handlers.MemoryHandler(
        capacity=1000,
        flushLevel=logging.CRITICAL + 1,
    )
    requests_logger.addHandler(handler)
    requests_logger.setLevel(logging.DEBUG)

    try:
        monitor = LoggingMonitor(owner="test-owner", repo="test-repo")
        asyncio.run(monitor.send_event(event))

        assert len(handler.buffer) == 0, (
            f"Expected no records on ghbot.requests logger, "
            f"but got {len(handler.buffer)}: {handler.buffer!r}"
        )
    finally:
        requests_logger.removeHandler(handler)
        requests_logger.setLevel(logging.NOTSET)
