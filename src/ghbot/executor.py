import asyncio
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

log = get_logger(__name__)

_DEFAULT_RETRY_AFTER = 60


class TaskPool:
    def __init__(self, limit: int = 16, network_error_threshold: int = 3) -> None:
        self._limit = limit
        self._network_error_threshold = network_error_threshold
        self._sem: asyncio.Semaphore
        self._tasks: list[asyncio.Task]
        self._aborted = False
        self._abort_reason: str | None = None
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
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        s = self.stats
        if self._aborted and self._abort_reason:
            raise FatalError(self._abort_reason)
        log.info(
            "completed: %d, not_found: %d, network_errors: %d",
            s["completed"],
            s["not_found"],
            s["network_error"],
        )

    async def submit(self, fn, *args: Any, **kwargs: Any) -> None:
        if self._aborted:
            return
        await self._sem.acquire()
        task = asyncio.create_task(self._run(fn, *args, **kwargs))
        self._tasks.append(task)

    async def _run(self, fn, *args: Any, **kwargs: Any) -> None:
        try:
            result = await fn(*args, **kwargs)
            self.results.append(result)
            self.stats["completed"] += 1
        except Exception as e:  # noqa: BLE001 - TaskPool records unexpected task failures.
            await self._handle_error(e, fn, args, kwargs)
        finally:
            self._sem.release()

    async def _handle_error(self, e: Exception, fn, args: Any, kwargs: Any) -> None:
        if isinstance(e, GitHubNotFoundError):
            self.stats["not_found"] += 1

        elif isinstance(e, GitHubPrimaryRateLimitError):
            self.stats["rate_limited"] += 1
            reset = getattr(
                getattr(e.__cause__, "rate_limit", None), "reset_datetime", None
            )
            reset_msg = f" Resets at {reset}." if reset else ""
            self._abort(
                f"Rate limited by GitHub API.{reset_msg} "
                f"completed: {self.stats['completed']}, rate_limited: {self.stats['rate_limited']}"
            )

        elif isinstance(e, GitHubSecondaryRateLimitError):
            self.stats["rate_limited"] += 1
            retry_after = _DEFAULT_RETRY_AFTER
            log.warning("Secondary rate limit hit, retrying after %ds", retry_after)
            await asyncio.sleep(retry_after)
            try:
                result = await fn(*args, **kwargs)
                self.results.append(result)
                self.stats["completed"] += 1
            except Exception:  # noqa: BLE001 - retry failure aborts regardless of exception type.
                self._abort(
                    f"Secondary rate limit retry failed. "
                    f"completed: {self.stats['completed']}, rate_limited: {self.stats['rate_limited']}"
                )

        elif isinstance(e, GitHubApiError) and isinstance(
            e.__cause__, (httpx.TransportError, gidgethub.GitHubBroken)
        ):
            self.stats["network_error"] += 1
            if self.stats["network_error"] >= self._network_error_threshold:
                n = self.stats["network_error"]
                self._abort(
                    f"Too many network errors ({n}). "
                    f"completed: {self.stats['completed']}, network_errors: {n}"
                )

        else:
            self.stats["unexpected"] += 1
            log.error("Unexpected error in task: %s", e)

    def _abort(self, reason: str) -> None:
        self._aborted = True
        self._abort_reason = reason
