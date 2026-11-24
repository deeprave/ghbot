"""Tests for the dependency-neutral repository scan runners."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import gidgethub.httpx as gh_httpx
import pytest

from ghbot.errors import AuthError, GitHubSecondaryRateLimitError
from ghbot.github.repos import DiscoveredRepository
from ghbot.processor import InfoRepoProcessor, RepoResult
from ghbot.runner import run_combo, run_mode, run_processor


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

        async def submit(self, fn, **kwargs):
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

        async def submit(self, fn, **kwargs):
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


@pytest.mark.anyio
async def test_run_combo_scans_once_and_groups_every_discovered_mode_result():
    class ImmediatePool:
        def __init__(self):
            self.stats = {}
            self.submissions = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn, **kwargs):
            self.submissions += 1
            await fn()

    github = MagicMock(spec=gh_httpx.GitHubAPI)
    pool = ImmediatePool()
    monitor = MagicMock()
    first_result = RepoResult(owner="acme", repo="api")
    second_result = RepoResult(owner="acme", repo="api")
    first_processor = MagicMock(run=AsyncMock(return_value=first_result))
    second_processor = MagicMock(run=AsyncMock(return_value=second_result))
    first_collection = MagicMock()
    second_collection = MagicMock()
    first_mode = MagicMock()
    first_mode.name = "drift"
    second_mode = MagicMock()
    second_mode.name = "security"
    first_mode.new_collection.return_value = first_collection
    second_mode.new_collection.return_value = second_collection
    first_mode.new_processor.return_value = first_processor
    second_mode.new_processor.return_value = second_processor
    options = {
        "drift": {"format": "json"},
        "security": {"format": "json"},
    }

    async def scan(owners, gh, *, explicit_repositories=None):
        yield DiscoveredRepository("acme", {"name": "api"}, "Organization")

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.gh_httpx.GitHubAPI", return_value=github),
        patch("ghbot.runner.scan_repositories", side_effect=scan) as scan_repositories,
        patch("ghbot.runner.TaskPool", return_value=pool),
        patch("ghbot.runner.LoggingMonitor", return_value=monitor),
    ):
        report = await run_combo(
            {"owners": ["acme"], "concurrency": 1},
            (first_mode, second_mode),
            options,
        )

    scan_repositories.assert_called_once_with(
        ["acme"], github, explicit_repositories=None
    )
    assert pool.submissions == 1
    assert [section.name for section in report.sections] == ["drift", "security"]
    for mode, mode_options in (
        (first_mode, options["drift"]),
        (second_mode, options["security"]),
    ):
        mode.new_processor.assert_called_once_with(
            "acme", "api", github, monitor, mode_options, owner_type="Organization"
        )
    first_collection.add.assert_called_once_with(first_result)
    second_collection.add.assert_called_once_with(second_result)


@pytest.mark.anyio
async def test_run_combo_retries_rate_limited_discovery_through_the_shared_gate():
    class ImmediatePool:
        def __init__(self):
            self.stats = {}
            self.rate_limit_abort = None
            self.completed_ids: set[str] = set()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn, *, task_id=None):
            await fn()
            if task_id is not None:
                self.completed_ids.add(task_id)

        def abort_rate_limit(self, error):
            self.rate_limit_abort = error

    calls = 0
    collection = MagicMock()
    mode = MagicMock()
    mode.name = "security"
    mode.new_collection.return_value = collection
    result = RepoResult(owner="acme", repo="api")
    mode.new_processor.return_value = MagicMock(run=AsyncMock(return_value=result))

    async def scan(owners, gh, *, explicit_repositories=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise GitHubSecondaryRateLimitError("limited", delay_seconds=0)
        yield DiscoveredRepository("acme", {"name": "api"}, "Organization")

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=scan),
        patch("ghbot.runner.TaskPool", return_value=ImmediatePool()),
    ):
        report = await run_combo({"owners": ["acme"], "concurrency": 1}, (mode,))

    assert calls == 2
    assert report.complete
    collection.add.assert_called_once_with(result)


@pytest.mark.anyio
async def test_run_combo_retains_other_mode_result_when_one_is_partial():
    class ImmediatePool:
        def __init__(self):
            self.stats = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn, **kwargs):
            await fn()

    partial = RepoResult(owner="acme", repo="api", status="partial")
    complete = RepoResult(owner="acme", repo="api")
    partial_collection = MagicMock()
    complete_collection = MagicMock()
    partial_mode = MagicMock()
    partial_mode.name = "drift"
    partial_mode.new_collection.return_value = partial_collection
    partial_mode.new_processor.return_value = MagicMock(
        run=AsyncMock(return_value=partial)
    )
    complete_mode = MagicMock()
    complete_mode.name = "security"
    complete_mode.new_collection.return_value = complete_collection
    complete_mode.new_processor.return_value = MagicMock(
        run=AsyncMock(return_value=complete)
    )

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_one),
        patch("ghbot.runner.TaskPool", return_value=ImmediatePool()),
    ):
        await run_combo(
            {"owners": ["acme"], "concurrency": 1},
            (partial_mode, complete_mode),
        )

    partial_collection.add.assert_called_once_with(partial)
    complete_collection.add.assert_called_once_with(complete)


@pytest.mark.anyio
async def test_run_combo_propagates_fatal_processor_errors():
    class ImmediatePool:
        def __init__(self):
            self.stats = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn, **kwargs):
            await fn()

    mode = MagicMock()
    mode.name = "security"
    mode.new_processor.return_value = MagicMock(
        run=AsyncMock(side_effect=AuthError("bad token"))
    )
    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_one),
        patch("ghbot.runner.TaskPool", return_value=ImmediatePool()),
        pytest.raises(AuthError, match="bad token"),
    ):
        await run_combo(
            {"owners": ["owner1"], "concurrency": 1},
            (mode,),
        )


@pytest.mark.anyio
async def test_run_combo_does_not_duplicate_results_after_secondary_rate_limit_retry(
    monkeypatch,
):
    async def no_sleep(_):
        pass

    monkeypatch.setattr("ghbot.executor.asyncio.sleep", no_sleep)

    drift_result = RepoResult(owner="acme", repo="api")
    issues_result = RepoResult(owner="acme", repo="api")
    drift_collection = MagicMock()
    issues_collection = MagicMock()
    drift_mode = MagicMock()
    drift_mode.name = "drift"
    drift_mode.new_collection.return_value = drift_collection
    drift_mode.new_processor.return_value = MagicMock(
        run=AsyncMock(side_effect=[drift_result, drift_result])
    )
    issues_mode = MagicMock()
    issues_mode.name = "issues"
    issues_mode.new_collection.return_value = issues_collection
    issues_mode.new_processor.return_value = MagicMock(
        run=AsyncMock(
            side_effect=[
                GitHubSecondaryRateLimitError("429", delay_seconds=0),
                issues_result,
            ]
        )
    )

    async def scan(owners, gh, *, explicit_repositories=None):
        yield DiscoveredRepository("acme", {"name": "api"}, "Organization")

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=scan),
    ):
        await run_combo(
            {"owners": ["acme"], "concurrency": 1},
            (drift_mode, issues_mode),
        )

    drift_collection.add.assert_called_once_with(drift_result)
    issues_collection.add.assert_called_once_with(issues_result)
    drift_mode.new_processor.return_value.run.assert_awaited_once_with()


@pytest.mark.anyio
async def test_run_combo_retains_completed_results_after_later_ordinary_failure():
    completed_result = RepoResult(owner="acme", repo="api")
    completed_collection = MagicMock()
    failed_collection = MagicMock()
    completed_mode = MagicMock()
    completed_mode.name = "security"
    completed_mode.new_collection.return_value = completed_collection
    completed_mode.new_processor.return_value = MagicMock(
        run=AsyncMock(return_value=completed_result)
    )
    failed_mode = MagicMock()
    failed_mode.name = "issues"
    failed_mode.new_collection.return_value = failed_collection
    failed_mode.new_processor.return_value = MagicMock(
        run=AsyncMock(side_effect=RuntimeError("unexpected failure"))
    )

    with (
        patch("ghbot.runner.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.runner.scan_repositories", side_effect=_scan_one),
    ):
        report = await run_combo(
            {"owners": ["acme"], "concurrency": 1},
            (completed_mode, failed_mode),
        )

    completed_collection.add.assert_called_once_with(completed_result)
    failed_collection.add.assert_not_called()
    assert report.sections[0].collection.complete
    assert not report.sections[1].collection.complete
