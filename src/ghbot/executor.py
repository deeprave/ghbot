import asyncio
from dataclasses import dataclass
from typing import Any, Self

import gidgethub
import httpx

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.log import get_logger
from ghbot.rate_limit import RateLimitGate

log = get_logger(__name__)

_DEFAULT_RETRY_AFTER = 60


@dataclass(frozen=True, slots=True)
class RateLimitAbort:
    """A rate-limit policy breach retained for report rendering."""

    reason: str


class TaskPool:
    def __init__(
        self,
        limit: int = 16,
        network_error_threshold: int = 3,
        rate_limit_gate: RateLimitGate | None = None,
        abort_grace_seconds: float = 5,
    ) -> None:
        self._limit = limit
        self._network_error_threshold = network_error_threshold
        self._sem: asyncio.Semaphore
        self._tasks: list[asyncio.Task]
        self._aborted = False
        self._abort_reason: str | None = None
        self._fatal_error: FatalError | None = None
        self._rate_limit_gate = rate_limit_gate
        self._abort_grace_seconds = abort_grace_seconds
        self.rate_limit_abort: RateLimitAbort | None = None
        self.skipped_explicit_ids: set[str] = set()
        self._rate_limit_abort_event: asyncio.Event | None = None
        self.completed_ids: set[str] = set()
        self.terminal_ids: set[str] = set()
        self.failed_ids: set[str] = set()
        self.results: list[Any] = []
        self.stats: dict[str, int] = {
            "completed": 0,
            "not_found": 0,
            "network_error": 0,
            "rate_limited": 0,
            "unexpected": 0,
        }

    async def __aenter__(self) -> Self:
        self._sem = asyncio.Semaphore(self._limit)
        self._tasks = []
        self._rate_limit_abort_event = asyncio.Event()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        if self._tasks:
            pending = set(self._tasks)
            abort_waiter: asyncio.Task[bool] | None = None
            if (
                self.rate_limit_abort is None
                and self._rate_limit_abort_event is not None
            ):
                abort_waiter = asyncio.create_task(self._rate_limit_abort_event.wait())
                try:
                    while pending and not abort_waiter.done():
                        _done, pending = await asyncio.wait(
                            pending | {abort_waiter},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        pending.discard(abort_waiter)
                finally:
                    abort_waiter.cancel()
                    await asyncio.gather(abort_waiter, return_exceptions=True)
            if pending:
                _, pending = await asyncio.wait(
                    pending, timeout=self._abort_grace_seconds
                )
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
        s = self.stats
        if self._fatal_error:
            raise self._fatal_error
        if self._aborted and self._abort_reason and self.rate_limit_abort is None:
            raise FatalError(self._abort_reason)
        log.info(
            "completed: %d, not_found: %d, network_errors: %d, rate_limit_episodes: %d, rate_limit_wait_seconds: %.1f",
            s["completed"],
            s["not_found"],
            s["network_error"],
            self._rate_limit_gate.hits if self._rate_limit_gate else 0,
            self._rate_limit_gate.total_wait_seconds if self._rate_limit_gate else 0,
        )

    async def submit(
        self, fn, *args: Any, task_id: str | None = None, **kwargs: Any
    ) -> None:
        if self._aborted:
            return
        await self._sem.acquire()
        if self._aborted:
            self._sem.release()
            return
        task = asyncio.create_task(self._run(fn, *args, task_id=task_id, **kwargs))
        self._tasks.append(task)

    async def _run(
        self, fn, *args: Any, task_id: str | None = None, **kwargs: Any
    ) -> None:
        try:
            result = await fn(*args, **kwargs)
            self.results.append(result)
            self.stats["completed"] += 1
            if task_id is not None:
                self.completed_ids.add(task_id)
        except Exception as e:  # noqa: BLE001 - TaskPool records unexpected task failures.
            await self._handle_error(e, fn, args, kwargs, task_id)
        finally:
            self._sem.release()

    async def _handle_error(
        self, e: Exception, fn, args: Any, kwargs: Any, task_id: str | None
    ) -> None:
        if isinstance(e, GitHubNotFoundError):
            self.stats["not_found"] += 1
            if task_id is not None:
                self.terminal_ids.add(task_id)

        elif isinstance(
            e, (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError)
        ):
            self.stats["rate_limited"] += 1
            if self._rate_limit_gate is None:
                await self._handle_legacy_rate_limit(e, fn, args, kwargs, task_id)
                return
            if self._aborted:
                return
            if not await self._rate_limit_gate.record(e):
                self._abort_rate_limit(e)
                return
            await self._rate_limit_gate.wait()
            if self._aborted:
                return
            try:
                result = await fn(*args, **kwargs)
                self.results.append(result)
                self.stats["completed"] += 1
                if task_id is not None:
                    self.completed_ids.add(task_id)
            except Exception as retry_error:  # noqa: BLE001 - preserve task error policy.
                await self._handle_error(retry_error, fn, args, kwargs, task_id)

        elif isinstance(e, GitHubApiError) and isinstance(
            e.__cause__, (httpx.TransportError, gidgethub.GitHubBroken)
        ):
            self.stats["network_error"] += 1
            if task_id is not None:
                self.failed_ids.add(task_id)
            if self.stats["network_error"] >= self._network_error_threshold:
                n = self.stats["network_error"]
                self._abort(
                    f"Too many network errors ({n}). "
                    f"completed: {self.stats['completed']}, network_errors: {n}"
                )

        elif isinstance(e, FatalError):
            self._fatal_error = e
            self._aborted = True

        else:
            self.stats["unexpected"] += 1
            if task_id is not None:
                self.failed_ids.add(task_id)
            log.error("Unexpected error in task: %s", e)

    def _abort(self, reason: str) -> None:
        self._aborted = True
        self._abort_reason = reason

    def _abort_rate_limit(
        self, error: GitHubPrimaryRateLimitError | GitHubSecondaryRateLimitError
    ) -> None:
        reset = f" Resets at {error.reset_at}." if error.reset_at else ""
        reason = (
            f"Rate limited by GitHub API.{reset} completed: {self.stats['completed']}, "
            f"rate_limited: {self.stats['rate_limited']}"
        )
        self._abort(reason)
        self.rate_limit_abort = RateLimitAbort(reason)
        if self._rate_limit_abort_event is not None:
            self._rate_limit_abort_event.set()

    def abort_rate_limit(
        self, error: GitHubPrimaryRateLimitError | GitHubSecondaryRateLimitError
    ) -> None:
        """Record a discovery-time policy breach without discarding prior tasks."""
        self.stats["rate_limited"] += 1
        self._abort_rate_limit(error)

    async def _handle_legacy_rate_limit(
        self,
        error: GitHubPrimaryRateLimitError | GitHubSecondaryRateLimitError,
        fn,
        args: Any,
        kwargs: Any,
        task_id: str | None,
    ) -> None:
        """Retain direct-pool behaviour for callers that have no shared gate."""
        if isinstance(error, GitHubPrimaryRateLimitError):
            self._abort(
                f"Rate limited by GitHub API. completed: {self.stats['completed']}"
            )
            return
        log.warning(
            "Secondary rate limit hit, retrying after %ds", _DEFAULT_RETRY_AFTER
        )
        await asyncio.sleep(_DEFAULT_RETRY_AFTER)
        try:
            result = await fn(*args, **kwargs)
            self.results.append(result)
            self.stats["completed"] += 1
            if task_id is not None:
                self.completed_ids.add(task_id)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            self._abort(
                f"Secondary rate limit retry failed. completed: {self.stats['completed']}, "
                f"rate_limited: {self.stats['rate_limited']}"
            )
        except FatalError as retry_error:
            self._fatal_error = retry_error
            self._aborted = True
        except Exception:  # noqa: BLE001 - retry failure aborts regardless of exception type.
            self._abort(
                f"Secondary rate limit retry failed. completed: {self.stats['completed']}, "
                f"rate_limited: {self.stats['rate_limited']}"
            )
