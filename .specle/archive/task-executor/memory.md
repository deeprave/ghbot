# Memory: Task Executor

## Key Decisions

- `TaskPool` uses `asyncio.Semaphore` for concurrency limiting and `asyncio.create_task` + `asyncio.gather` for task lifecycle — no `TaskGroup` (its cancel-all behaviour on first exception is incompatible with the per-task error policy).
- Per-task exception wrapping lives in `_run()` — the `try/except Exception` there prevents any single task failure from propagating to the gather call. `TaskGroup` was explicitly ruled out for this reason.
- `_abort()` sets `_aborted = True` and stores the reason string; `__aexit__` raises `FatalError` after `gather` completes. This guarantees in-flight tasks always finish before the error surfaces.
- `submit()` checks `_aborted` before acquiring the semaphore — it becomes a no-op immediately after any abort trigger, without needing a separate flag check inside `_run`.
- Secondary rate limit retry is inlined in `_handle_error` (not a separate retry loop) — the retry is a one-shot special case, not a general retry mechanism.
- Network error classification uses `isinstance(e.__cause__, (httpx.TransportError, gidgethub.GitHubBroken))` — relies on `github_api_call` always chaining the original exception via `raise ... from e`. This is a contract between `client.py` and `executor.py`.
- Plain 403 (access denied) is mapped to `GitHubNotFoundError` in `github_api_call`, not in `TaskPool` — the pool never sees a raw 403. This keeps the pool's error policy clean and status-code-free.
- `RateLimitExceeded` must be caught before `HTTPException` in `github_api_call` because it is a subclass. The existing `_RETRYABLE` tuple pattern was extended to document catch order via code structure.
- `GitHubPrimaryRateLimitError` carries the original exception as `__cause__`, allowing `TaskPool` to extract `e.__cause__.rate_limit.reset_datetime` for the abort message without adding attributes to the error class itself.

## Patterns Used

### Per-task exception wrapping with `asyncio.create_task` + `gather`
```python
async def _run(self, fn, *args, **kwargs):
    try:
        result = await fn(*args, **kwargs)
        self.results.append(result)
        self.stats["completed"] += 1
    except Exception as e:
        await self._handle_error(e, fn, args, kwargs)
    finally:
        self._sem.release()


async def __aexit__(self, *exc_info):
    if self._tasks:
        await asyncio.gather(*self._tasks, return_exceptions=True)
    if self._aborted and self._abort_reason:
        raise FatalError(self._abort_reason)
    log.info("completed: %d, not_found: %d, network_errors: %d", ...)
```
`return_exceptions=True` on `gather` ensures all tasks are awaited even if some raise — but since `_run` already swallows exceptions, this is belt-and-suspenders.

### Abort via flag + deferred raise
```python
def _abort(self, reason: str) -> None:
    self._aborted = True
    self._abort_reason = reason


async def submit(self, fn, *args, **kwargs) -> None:
    if self._aborted:
        return  # no-op
    await self._sem.acquire()
    ...
```
Abort is non-cancelling — it just stops new work from entering and defers the `FatalError` to `__aexit__`.

### Secondary rate limit one-shot retry in `_handle_error`
```python
elif isinstance(e, GitHubSecondaryRateLimitError):
    self.stats["rate_limited"] += 1
    await asyncio.sleep(retry_after)
    try:
        result = await fn(*args, **kwargs)
        self.results.append(result)
        self.stats["completed"] += 1
    except Exception:
        self._abort("Secondary rate limit retry failed. ...")
```
The retry is a direct `await fn(...)` call — no loop, no recursion. Second failure calls `_abort` and returns; the deferred raise happens in `__aexit__`.

### Network error classification via `__cause__`
```python
elif isinstance(e, GitHubApiError) and isinstance(
    e.__cause__, (httpx.TransportError, gidgethub.GitHubBroken)
):
    self.stats["network_error"] += 1
    if self.stats["network_error"] >= self._network_error_threshold:
        self._abort(f"Too many network errors ({n}). ...")
```
Relies on `github_api_call` using `raise GitHubApiError(...) from e` — the original transport exception is always the `__cause__`.

### Concurrency test via `asyncio.sleep` + peak tracking
```python
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
```
The `await asyncio.sleep(0.01)` yields control so other tasks can start, making the peak measurement meaningful.

### Monkeypatching `asyncio.sleep` in executor tests
```python
monkeypatch.setattr("ghbot.executor.asyncio.sleep", fake_sleep)
```
Patches the `asyncio` reference as imported in `executor.py` — avoids real delays in tests while still verifying the sleep was called.

## Lessons Learned

- **`asyncio.TaskGroup` is wrong for independent-task pools**: its cancel-all-on-first-exception semantics directly contradict the "tasks are independent" requirement. `create_task` + `gather(return_exceptions=True)` is the right primitive.
- **`return_exceptions=True` on gather is belt-and-suspenders**: since `_run` catches all exceptions internally, `gather` will never see a raised exception from a task. But it's still correct to pass `return_exceptions=True` to make the intent explicit.
- **Semaphore release in `finally`**: always release in `finally`, not in the happy path — otherwise an exception in `_handle_error` (e.g. during secondary retry) would leak a semaphore slot and eventually deadlock `submit()`.
- **`_abort` is idempotent by design**: multiple tasks can call `_abort` concurrently (e.g. two rate limit errors). The second call overwrites `_abort_reason` but `_aborted` stays `True` — this is acceptable since only one `FatalError` is raised.
- **`monkeypatch` over `patch` for module-level names**: `monkeypatch.setattr("ghbot.executor.asyncio.sleep", ...)` is cleaner than `unittest.mock.patch` for simple attribute replacement in tests.
- **`gidgethub.RateLimitExceeded` constructor takes `rate_limit=None`**: in tests, `raise gidgethub.RateLimitExceeded(rate_limit=None)` is the minimal valid construction — the `rate_limit` attribute may be `None` and the pool handles this gracefully (`getattr(..., None)` chain).
- **`http.HTTPStatus` enum in tests**: using `gidgethub.BadRequest(http.HTTPStatus.TOO_MANY_REQUESTS)` is cleaner than raw integer status codes and self-documents the intent.

## Follow-ups

- `_abort_reason` is overwritten if multiple tasks abort concurrently — the last writer wins. Consider storing the first reason instead (set only if `not self._aborted`).
- `_DEFAULT_RETRY_AFTER = 60` is hardcoded; the spec mentions reading `Retry-After` from the response header. This is not yet implemented — `GitHubSecondaryRateLimitError` would need to carry the header value.
- `pool.stats` is mutated from concurrent tasks without a lock — safe in asyncio (single-threaded event loop) but worth a comment for future readers who might consider threading.
- The pool is not reusable after exit (no reset mechanism). If reuse is ever needed, `__aenter__` would need to reinitialise `_tasks`, `results`, `stats`, and `_aborted`.
- `submit()` acquires the semaphore before creating the task — if `create_task` raises (unlikely but possible), the semaphore slot is leaked. The `finally` in `_run` only covers the task body, not task creation.
