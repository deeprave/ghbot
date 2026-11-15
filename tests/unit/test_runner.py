"""Tests for the dependency-neutral repository scan runners."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import gidgethub.httpx as gh_httpx
import pytest

from ghbot.errors import AuthError
from ghbot.github.repos import DiscoveredRepository
from ghbot.processor import InfoRepoProcessor, RepoResult
from ghbot.runner import run_mode, run_processor


async def _scan_one(owners, gh, *, explicit_repositories=None):
    yield DiscoveredRepository("owner1", {"name": "repo1"}, "User")


async def _scan_none(owners, gh, *, explicit_repositories=None):
    return
    yield


def _pool(*, results=None, stats=None):
    pool = AsyncMock()
    pool.__aenter__ = AsyncMock(return_value=pool)
    pool.__aexit__ = AsyncMock(return_value=False)
    pool.results = results or []
    pool.stats = stats or {}
    return pool


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("runner", "arguments"),
    [
        (run_processor, ({"owners": [], "concurrency": 1}, InfoRepoProcessor)),
        (run_mode, ({"owners": [], "concurrency": 1}, MagicMock())),
    ],
)
async def test_runners_propagate_fatal_authentication_errors(runner, arguments):
    with (
        patch(
            "ghbot.runner.get_auth_token",
            new=AsyncMock(side_effect=AuthError("bad token")),
        ),
        pytest.raises(AuthError, match="bad token"),
    ):
        await runner(*arguments)


@pytest.mark.anyio
async def test_run_processor_discovers_repositories_and_constructs_processors():
    github = MagicMock(spec=gh_httpx.GitHubAPI)
    pool = _pool()
    monitor = AsyncMock()
    processor = MagicMock(run=AsyncMock())
    processor_cls = MagicMock(return_value=processor)
    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.gh_httpx.GitHubAPI", return_value=github),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_one) as scan,
        patch("ghbot.runner.TaskPool", return_value=pool),
        patch("ghbot.runner.LoggingMonitor", return_value=monitor),
    ):
        await run_processor({"owners": ["owner1"], "concurrency": 16}, processor_cls)

    scan.assert_called_once_with(["owner1"], github, explicit_repositories=None)
    processor_cls.assert_called_once_with(
        "owner1", "repo1", github, monitor, options=None, owner_type="User"
    )
    pool.submit.assert_awaited_once_with(processor.run)


@pytest.mark.anyio
async def test_run_processor_propagates_options_and_owner_type():
    github = MagicMock(spec=gh_httpx.GitHubAPI)
    pool = _pool()
    processor = MagicMock(run=AsyncMock())
    processor_cls = MagicMock(return_value=processor)

    async def organisation(owners, gh, *, explicit_repositories=None):
        yield DiscoveredRepository("acme", {"name": "private"}, "Organization")

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.gh_httpx.GitHubAPI", return_value=github),
        patch("ghbot.runner.scan_repositories", side_effect=organisation),
        patch("ghbot.runner.TaskPool", return_value=pool),
    ):
        await run_processor(
            {"owners": ["acme"], "concurrency": 1}, processor_cls, {"format": "json"}
        )

    assert processor_cls.call_args.kwargs == {
        "options": {"format": "json"},
        "owner_type": "Organization",
    }


@pytest.mark.anyio
async def test_run_processor_forwards_explicit_repositories_to_scanner():
    github = MagicMock(spec=gh_httpx.GitHubAPI)
    pool = _pool()
    explicit_repositories = (("acme", "widgets"),)

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.gh_httpx.GitHubAPI", return_value=github),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_none) as scan,
        patch("ghbot.runner.TaskPool", return_value=pool),
    ):
        await run_processor(
            {
                "owners": ["ignored"],
                "concurrency": 1,
                "explicit_repositories": explicit_repositories,
            },
            InfoRepoProcessor,
        )

    scan.assert_called_once_with(
        ["ignored"], github, explicit_repositories=explicit_repositories
    )


@pytest.mark.anyio
async def test_run_processor_selects_environment_authentication():
    pool = _pool()
    with (
        patch(
            "ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")
        ) as auth,
        patch("ghbot.runner.TaskPool", return_value=pool),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_none),
    ):
        await run_processor(
            {"owners": [], "concurrency": 1, "env": True}, InfoRepoProcessor
        )

    auth.assert_awaited_once_with(use_environment=True)


@pytest.mark.anyio
async def test_run_processor_logs_pool_stats(caplog):
    pool = _pool(stats={"completed": 1})
    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.TaskPool", return_value=pool),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_none),
        caplog.at_level(logging.INFO),
    ):
        await run_processor({"owners": [], "concurrency": 1}, InfoRepoProcessor)

    assert any("stats" in record.message for record in caplog.records)


@pytest.mark.anyio
async def test_run_mode_collects_results_inside_pool_tasks():
    class ImmediatePool:
        def __init__(self):
            self.stats = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn):
            await fn()

    result = RepoResult(owner="acme", repo="api")
    processor = MagicMock(run=AsyncMock(return_value=result))
    collection = MagicMock()
    mode = MagicMock()
    mode.new_collection.return_value = collection
    mode.new_processor.return_value = processor

    captured: list[object] = []

    async def scan(owners, gh, *, explicit_repositories=None):
        captured.append(explicit_repositories)
        yield DiscoveredRepository("acme", {"name": "api"}, "Organization")

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=scan),
        patch("ghbot.runner.TaskPool", return_value=ImmediatePool()),
    ):
        await run_mode(
            {"owners": ["acme"], "concurrency": 1, "explicit_repositories": None},
            mode,
            {"labels": True},
        )

    mode.new_processor.assert_called_once()
    assert mode.new_processor.call_args.kwargs["owner_type"] == "Organization"
    collection.add.assert_called_once_with(result)
    assert captured == [None]


@pytest.mark.anyio
async def test_run_mode_forwards_explicit_repositories_to_scanner():
    class EmptyPool:
        def __init__(self):
            self.stats = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn):
            await fn()

    explicit_repositories = (("acme", "widgets"),)
    mode = MagicMock()
    captured: list[object] = []

    async def scan(owners, gh, *, explicit_repositories=None):
        captured.append(explicit_repositories)
        return
        yield

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=scan),
        patch("ghbot.runner.TaskPool", return_value=EmptyPool()),
    ):
        await run_mode(
            {
                "owners": ["ignored"],
                "concurrency": 1,
                "explicit_repositories": explicit_repositories,
            },
            mode,
        )

    assert captured == [explicit_repositories]
