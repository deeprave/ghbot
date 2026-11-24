import asyncio

import pytest

from ghbot.errors import GitHubSecondaryRateLimitError
from ghbot.rate_limit import RateLimitGate


@pytest.mark.anyio
async def test_gate_waits_for_a_recorded_rate_limit_without_real_sleep():
    now = 10.0
    waits: list[float] = []

    async def sleep(delay: float) -> None:
        nonlocal now
        waits.append(delay)
        now += delay

    gate = RateLimitGate(
        max_wait=120,
        max_hits=3,
        clock=lambda: now,
        sleep=sleep,
        retry_jitter=lambda: 0,
    )
    assert await gate.record(GitHubSecondaryRateLimitError("limited", delay_seconds=5))

    await gate.wait()

    assert waits == [5]


@pytest.mark.anyio
async def test_gate_coalesces_limits_that_arrive_during_one_active_block():
    now = 10.0
    gate = RateLimitGate(
        max_wait=120,
        max_hits=1,
        clock=lambda: now,
        retry_jitter=lambda: 0,
    )

    assert await gate.record(GitHubSecondaryRateLimitError("limited", delay_seconds=5))
    assert await gate.record(GitHubSecondaryRateLimitError("limited", delay_seconds=5))

    assert gate.hits == 1


@pytest.mark.anyio
async def test_gate_staggers_all_waiters_after_the_shared_block():
    now = 10.0
    waits: list[float] = []
    initial_waits = 0
    waiting = asyncio.Event()
    release = asyncio.Event()

    async def sleep(delay: float) -> None:
        nonlocal initial_waits
        waits.append(delay)
        if initial_waits < 2:
            assert delay == 5
            initial_waits += 1
            if initial_waits == 2:
                waiting.set()
            await release.wait()

    gate = RateLimitGate(
        max_wait=120,
        max_hits=3,
        clock=lambda: now,
        sleep=sleep,
        retry_jitter=lambda: 8,
    )
    assert await gate.record(GitHubSecondaryRateLimitError("limited", delay_seconds=5))

    waiters = [asyncio.create_task(gate.wait()) for _ in range(2)]
    await waiting.wait()
    now += 5
    release.set()
    await asyncio.gather(*waiters)

    assert waits == [5, 5, 5, 5]


@pytest.mark.anyio
async def test_gate_rechecks_a_block_renewed_during_retry_jitter():
    now = 0.0
    waits: list[float] = []

    async def sleep(delay: float) -> None:
        nonlocal now
        waits.append(delay)
        now += delay
        if delay == 1:
            assert await gate.record(
                GitHubSecondaryRateLimitError("renewed", delay_seconds=2)
            )

    gate = RateLimitGate(
        max_wait=10, max_hits=3, clock=lambda: now, sleep=sleep, retry_jitter=lambda: 1
    )
    assert await gate.record(GitHubSecondaryRateLimitError("limited", delay_seconds=5))

    await gate.wait()

    assert waits == [5, 1, 2]
