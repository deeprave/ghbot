import asyncio

import httpx
import pytest

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.executor import TaskPool

# --- result collection and concurrency ---


@pytest.mark.anyio
async def test_results_collected():
    async def task(x):
        return {"x": x}

    async with TaskPool(limit=4) as pool:
        for i in range(3):
            await pool.submit(task, i)

    assert sorted(pool.results, key=lambda r: r["x"]) == [{"x": 0}, {"x": 1}, {"x": 2}]
    assert pool.stats["completed"] == 3


@pytest.mark.anyio
async def test_concurrency_limited():
    active = 0
    peak = 0

    async def task():
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {}

    async with TaskPool(limit=2) as pool:
        for _ in range(6):
            await pool.submit(task)

    assert peak <= 2


# --- error policy ---


@pytest.mark.anyio
async def test_not_found_counted_and_skipped():
    async def task():
        raise GitHubNotFoundError("404")

    async with TaskPool() as pool:
        await pool.submit(task)

    assert pool.stats["not_found"] == 1
    assert pool.results == []


@pytest.mark.anyio
async def test_primary_rate_limit_aborts_and_raises_fatal_error():
    async def task():
        raise GitHubPrimaryRateLimitError("rate limited")

    with pytest.raises(FatalError, match="Rate limited"):
        async with TaskPool() as pool:
            await pool.submit(task)

    assert pool.stats["rate_limited"] == 1


@pytest.mark.anyio
async def test_secondary_rate_limit_retries_and_succeeds(monkeypatch):
    calls = []

    async def fake_sleep(_):
        calls.append("sleep")

    monkeypatch.setattr("ghbot.executor.asyncio.sleep", fake_sleep)

    attempt = 0

    async def task():
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise GitHubSecondaryRateLimitError("429")
        return {"ok": True}

    async with TaskPool() as pool:
        await pool.submit(task)

    assert pool.results == [{"ok": True}]
    assert calls == ["sleep"]


@pytest.mark.anyio
async def test_secondary_rate_limit_second_failure_aborts(monkeypatch):
    async def fake_sleep(_):
        pass

    monkeypatch.setattr("ghbot.executor.asyncio.sleep", fake_sleep)

    async def task():
        raise GitHubSecondaryRateLimitError("429")

    with pytest.raises(FatalError):
        async with TaskPool() as pool:
            await pool.submit(task)


@pytest.mark.anyio
async def test_network_errors_below_threshold_no_abort():
    async def task():
        e = GitHubApiError("network")
        e.__cause__ = httpx.TransportError("conn")
        raise e

    async with TaskPool(network_error_threshold=3) as pool:
        await pool.submit(task)
        await pool.submit(task)

    assert pool.stats["network_error"] == 2


@pytest.mark.anyio
async def test_network_errors_at_threshold_aborts():
    async def task():
        e = GitHubApiError("network")
        e.__cause__ = httpx.TransportError("conn")
        raise e

    with pytest.raises(FatalError, match="Too many network errors"):
        async with TaskPool(network_error_threshold=3) as pool:
            for _ in range(3):
                await pool.submit(task)

    assert pool.stats["network_error"] == 3


@pytest.mark.anyio
async def test_unexpected_error_logged_and_counted(caplog):
    import logging

    async def task():
        raise ValueError("oops")

    with caplog.at_level(logging.ERROR):
        async with TaskPool() as pool:
            await pool.submit(task)

    assert pool.stats["unexpected"] == 1
    assert pool.results == []
    assert any("oops" in r.message for r in caplog.records)


# --- abort and exit behaviour ---


@pytest.mark.anyio
async def test_submit_is_noop_after_abort():
    called = 0

    async def rate_limit_task():
        raise GitHubPrimaryRateLimitError("rate limited")

    async def counting_task():
        nonlocal called
        called += 1
        return {}

    with pytest.raises(FatalError):
        async with TaskPool() as pool:
            await pool.submit(rate_limit_task)
            await asyncio.sleep(0)
            await pool.submit(counting_task)

    assert called == 0


@pytest.mark.anyio
async def test_inflight_tasks_finish_before_fatal_error():
    finished = []

    async def slow_task():
        await asyncio.sleep(0.02)
        finished.append(1)
        return {}

    async def rate_limit_task():
        raise GitHubPrimaryRateLimitError("rate limited")

    with pytest.raises(FatalError):
        async with TaskPool(limit=2) as pool:
            await pool.submit(slow_task)
            await pool.submit(rate_limit_task)

    assert len(finished) == 1


@pytest.mark.anyio
async def test_clean_exit_logs_summary(caplog):
    import logging

    async def task():
        return {}

    with caplog.at_level(logging.INFO):
        async with TaskPool() as pool:
            await pool.submit(task)

    assert any("completed" in r.message for r in caplog.records)
