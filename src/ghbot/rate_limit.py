"""Per-run admission control for GitHub rate-limit recovery."""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from ghbot.errors import GitHubRateLimitError
from ghbot.log import get_logger

log = get_logger(__name__)

_MAX_RETRY_JITTER_SECONDS = 5.0


def _retry_jitter() -> float:
    """Return a small delay that desynchronizes requests after a shared pause."""
    return random.uniform(0, _MAX_RETRY_JITTER_SECONDS)


class RateLimitGate:
    """Pause new API requests after a recoverable GitHub limit."""

    def __init__(
        self,
        *,
        max_wait: int,
        max_hits: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        retry_jitter: Callable[[], float] = _retry_jitter,
    ) -> None:
        self.max_wait = max_wait
        self.max_hits = max_hits
        self._clock = clock
        self._sleep = sleep
        self._retry_jitter = retry_jitter
        self._lock = asyncio.Lock()
        self._blocked_until = 0.0
        self._episode_started_at: float | None = None
        self.hits = 0
        self.total_wait_seconds = 0.0

    async def record(self, error: GitHubRateLimitError) -> bool:
        """Record a limit and return whether it is recoverable under policy."""
        delay = error.delay_seconds
        if delay is None and error.reset_at is not None:
            reset_at = error.reset_at
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=UTC)
            delay = max(0, int((reset_at - datetime.now(UTC)).total_seconds()))
        if delay is None:
            return False
        if delay > self.max_wait:
            return False
        async with self._lock:
            now = self._clock()
            if self._blocked_until > now:
                previous_until = self._blocked_until
                extended_until = max(self._blocked_until, now + delay)
                if (
                    self._episode_started_at is not None
                    and extended_until - self._episode_started_at > self.max_wait
                ):
                    return False
                self._blocked_until = extended_until
                self.total_wait_seconds += extended_until - previous_until
                log.debug("GitHub rate limit joined active wait")
                return True
            next_hits = self.hits + 1
            if next_hits > self.max_hits:
                return False
            self.hits = next_hits
            self._blocked_until = now + delay
            self._episode_started_at = now
            self.total_wait_seconds += delay
            log.warning(
                "GitHub rate limit: waiting %ds (hit %d/%d, reset=%s)",
                delay,
                self.hits,
                self.max_hits,
                error.reset_at.isoformat() if error.reset_at else "unknown",
            )
            return True

    async def wait(self) -> None:
        """Wait until the shared block expires, rechecking after every wake-up."""
        waited = False
        jittered = False
        while True:
            async with self._lock:
                delay = self._blocked_until - self._clock()
            if delay <= 0:
                if waited and not jittered:
                    jitter = min(
                        max(float(self._retry_jitter()), 0.0), _MAX_RETRY_JITTER_SECONDS
                    )
                    if jitter:
                        await self._sleep(jitter)
                    jittered = True
                    continue
                return
            waited = True
            await self._sleep(delay)
