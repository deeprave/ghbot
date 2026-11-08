from base64 import b64encode
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghbot.errors import (
    AuthError,
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.processor import DriftRepoProcessor, FeedbackEvent, RepoProcessor


class RecordingMonitor:
    def __init__(self) -> None:
        self.events: list[FeedbackEvent] = []

    async def send_event(self, event: FeedbackEvent) -> None:
        self.events.append(event)


def test_constructor_validates_owner_and_repo_and_satisfies_protocol():
    gh = _make_gh()
    monitor = RecordingMonitor()
    with pytest.raises(ValueError, match="owner"):
        DriftRepoProcessor("", "widgets", gh, monitor)
    with pytest.raises(ValueError, match="repo"):
        DriftRepoProcessor("acme", "", gh, monitor)
    assert isinstance(DriftRepoProcessor("acme", "widgets", gh, monitor), RepoProcessor)


@asynccontextmanager
async def _passthrough_github_api_call(gh):
    yield


def _workflow_blob(text: str) -> dict[str, str]:
    return {"content": b64encode(text.encode()).decode(), "encoding": "base64"}


def _make_gh(
    *, ahead_by: int = 3, workflows: list[str] | None = None, truncated: bool = False
):
    gh = MagicMock()
    workflows = workflows or []

    async def getitem(url, *, url_vars=None):
        if "/releases/latest" in url:
            return {"tag_name": "v1.2.0", "published_at": "2026-11-01T00:00:00Z"}
        if "/compare/" in url:
            assert url_vars == {
                "owner": "acme",
                "repo": "widgets",
                "basehead": "v1.2.0...trunk",
            }
            return {"ahead_by": ahead_by}
        if "/git/trees/" in url:
            return {
                "truncated": truncated,
                "tree": [
                    {
                        "path": f".github/workflows/{i}.yaml",
                        "type": "blob",
                        "sha": str(i),
                    }
                    for i, _ in enumerate(workflows)
                ],
            }
        if "/git/blobs/" in url:
            sha = url_vars["sha"]
            return _workflow_blob(workflows[int(sha)])
        return {"default_branch": "trunk"}

    gh.getitem = AsyncMock(side_effect=getitem)
    return gh


@pytest.mark.anyio
async def test_records_commits_since_latest_release_on_default_branch():
    processor = DriftRepoProcessor("acme", "widgets", _make_gh(), RecordingMonitor())
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.status == "success"
    assert result.results == {
        "latest_release_tag": "v1.2.0",
        "latest_release_published_at": "2026-11-01T00:00:00Z",
        "default_branch": "trunk",
        "commits_since_release": 3,
        "pypi_publishing_configured": False,
    }


@pytest.mark.anyio
async def test_no_latest_release_is_a_successful_non_reportable_result():
    gh = _make_gh()
    gh.getitem = AsyncMock(side_effect=GitHubNotFoundError("no release"))
    monitor = RecordingMonitor()
    processor = DriftRepoProcessor("acme", "widgets", gh, monitor)
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.status == "success"
    assert result.results["latest_release_tag"] is None
    assert result.results["commits_since_release"] is None


@pytest.mark.anyio
async def test_zero_commits_is_not_reportable():
    processor = DriftRepoProcessor(
        "acme", "widgets", _make_gh(ahead_by=0), RecordingMonitor()
    )
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.status == "success"
    assert result.results["commits_since_release"] == 0
    assert result.results["pypi_publishing_configured"] is None


@pytest.mark.anyio
async def test_detects_pypi_workflow_configuration():
    processor = DriftRepoProcessor(
        "acme",
        "widgets",
        _make_gh(workflows=["name: Publish to PyPI\n"]),
        RecordingMonitor(),
    )
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.results["pypi_publishing_configured"] is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    "signal", ["uses: pypa/gh-action-pypi-publish", "url: pypi.org"]
)
async def test_detects_explicit_pypi_workflow_signals(signal):
    processor = DriftRepoProcessor(
        "acme", "widgets", _make_gh(workflows=[signal]), RecordingMonitor()
    )
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()
    assert result.results["pypi_publishing_configured"] is True


@pytest.mark.anyio
async def test_workflow_failure_keeps_reportable_result_as_partial():
    gh = _make_gh(workflows=["name: build\n"])
    original_getitem = gh.getitem.side_effect

    async def getitem(url, *, url_vars=None):
        if "/git/blobs/" in url:
            raise GitHubApiError("workflow unavailable")
        return await original_getitem(url, url_vars=url_vars)

    gh.getitem = AsyncMock(side_effect=getitem)
    monitor = RecordingMonitor()
    processor = DriftRepoProcessor("acme", "widgets", gh, monitor)
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.status == "partial"
    assert result.results["commits_since_release"] == 3
    assert result.results["pypi_publishing_configured"] is None


@pytest.mark.anyio
async def test_truncated_workflow_tree_is_an_unknown_partial_result():
    processor = DriftRepoProcessor(
        "acme", "widgets", _make_gh(truncated=True), RecordingMonitor()
    )
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.status == "partial"
    assert result.results["commits_since_release"] == 3
    assert result.results["pypi_publishing_configured"] is None


@pytest.mark.anyio
async def test_compare_failure_is_partial_and_not_reportable():
    gh = _make_gh()
    original_getitem = gh.getitem.side_effect

    async def getitem(url, *, url_vars=None):
        if "/compare/" in url:
            raise GitHubApiError("comparison unavailable")
        return await original_getitem(url, url_vars=url_vars)

    gh.getitem = AsyncMock(side_effect=getitem)
    monitor = RecordingMonitor()
    processor = DriftRepoProcessor("acme", "widgets", gh, monitor)
    with patch("ghbot.processor.github_api_call", _passthrough_github_api_call):
        result = await processor.run()

    assert result.status == "partial"
    assert result.results["commits_since_release"] is None
    assert any(
        event.type == "fetch" and event.severity == "error" for event in monitor.events
    )


@pytest.mark.anyio
async def test_rate_limit_propagates():
    gh = _make_gh()
    gh.getitem = AsyncMock(side_effect=GitHubPrimaryRateLimitError("limited"))
    processor = DriftRepoProcessor("acme", "widgets", gh, RecordingMonitor())
    with (
        patch("ghbot.processor.github_api_call", _passthrough_github_api_call),
        pytest.raises(GitHubPrimaryRateLimitError),
    ):
        await processor.run()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error",
    [AuthError("authentication failed"), GitHubSecondaryRateLimitError("slow down")],
)
async def test_fatal_errors_propagate(error):
    gh = _make_gh()
    gh.getitem = AsyncMock(side_effect=error)
    processor = DriftRepoProcessor("acme", "widgets", gh, RecordingMonitor())
    with (
        patch("ghbot.processor.github_api_call", _passthrough_github_api_call),
        pytest.raises(type(error)),
    ):
        await processor.run()
