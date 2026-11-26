# Spec: Task Executor

## Problem / Context

ghbot needs to process many repositories concurrently without overwhelming the GitHub API
or the local machine. A bounded task pool runs up to N coroutines concurrently, collects
their results, and applies an intelligent error policy — ignoring recoverable errors,
aborting on rate limits, and aborting after too many network failures.

---

## Requirements

### Functional

1. `TaskPool(limit, network_error_threshold)` is an async context manager in `src/ghbot/executor.py`
2. `await pool.submit(coro, *args, **kwargs)` queues a coroutine; blocks if `limit` slots are full
3. Tasks run concurrently up to `limit` (default 16); `submit()` resumes as soon as a slot frees
4. Each task must return a `dict`; results are collected into `pool.results: list[dict]`
5. `pool.stats` is a `dict` with counts: `completed`, `not_found`, `network_error`, `rate_limited`, `unexpected`
6. Error policy (applied per task, no cancel-all):
   - `GitHubNotFoundError` → increment `stats["not_found"]`, skip (no result appended)
   - `GitHubPrimaryRateLimitError` (wraps gidgethub `RateLimitExceeded`, 403) → increment `stats["rate_limited"]`, abort immediately; include reset time in message if available
   - `GitHubSecondaryRateLimitError` (429) → increment `stats["rate_limited"]`, sleep `Retry-After` seconds (default 60s), retry once; second failure → abort pool
   - `GitHubApiError` that is network-related (`httpx.TransportError`, `gidgethub.GitHubBroken`) → increment `stats["network_error"]`; if count reaches `network_error_threshold` (default 3) → abort pool
   - `GitHubApiError` plain 403 (access denied) → treat as not_found: increment `stats["not_found"]`, skip
   - Any other exception → increment `stats["unexpected"]`, log error, skip
7. "Abort" means: stop accepting new `submit()` calls, wait for in-flight tasks to finish, then raise `FatalError` with a summary message
8. On clean exit, log a summary at INFO: `"completed: {n}, not_found: {n}, network_errors: {n}"`
9. `GitHubPrimaryRateLimitError(GitHubApiError)` and `GitHubSecondaryRateLimitError(GitHubApiError)` added to `errors.py`
10. `github_api_call` translates:
    - `gidgethub.RateLimitExceeded` (403) → `GitHubPrimaryRateLimitError` (carries `rate_limit` from original exception)
    - `HTTPException` 429 → `GitHubSecondaryRateLimitError`
    - `HTTPException` 403 plain → `GitHubNotFoundError` (access denied, skip)
    - `HTTPException` 404 → `GitHubNotFoundError`
    - other `HTTPException` → `GitHubApiError`

### Non-functional

- Tasks are independent — one failure never cancels siblings
- `submit()` is the only public method; results/stats are read after context manager exits
- Pool is not reusable after exit

---

## Constraints

- `asyncio.Semaphore` for concurrency limiting
- `asyncio.TaskGroup` used internally with per-task exception wrapping (no bare TaskGroup)
- No new dependencies

---

## High-level Design

```
src/ghbot/
├── executor.py        # TaskPool
├── errors.py          # + GitHubRateLimitError
src/ghbot/github/
├── client.py          # + 429 → GitHubRateLimitError
```

### Error class addition

```python
class GitHubPrimaryRateLimitError(
    GitHubApiError
): ...  # gidgethub RateLimitExceeded (403)


class GitHubSecondaryRateLimitError(GitHubApiError): ...  # 429 Too Many Requests
```

### github_api_call exception mapping

| Exception | Condition | Raises |
|---|---|---|
| `gidgethub.RateLimitExceeded` | — | `GitHubPrimaryRateLimitError` (carries `rate_limit`) |
| `gidgethub.HTTPException` | 429 | `GitHubSecondaryRateLimitError` |
| `gidgethub.HTTPException` | 403 (plain) | `GitHubNotFoundError` (access denied) |
| `gidgethub.HTTPException` | 404 | `GitHubNotFoundError` |
| `gidgethub.HTTPException` | other | `GitHubApiError` |
| `gidgethub.GitHubBroken` / `httpx.TransportError` | — | sleep 1s → `GitHubApiError` |

Note: `RateLimitExceeded` must be caught before `HTTPException` (it's a subclass).

### TaskPool sketch

```python
class TaskPool:
    def __init__(self, limit: int = 16, network_error_threshold: int = 3): ...
    async def __aenter__(self) -> "TaskPool": ...
    async def __aexit__(
        self, *exc_info
    ) -> None: ...  # waits for all tasks, logs summary
    async def submit(
        self, fn, *args, **kwargs
    ) -> None: ...  # blocks if full, no-op if aborted

    results: list[dict]
    stats: dict  # completed, not_found, network_error, rate_limited, unexpected
```

### Network error classification

A `GitHubApiError` is network-related if it wraps `httpx.TransportError` or `gidgethub.GitHubBroken` — i.e. raised by the sleep-then-raise path in `github_api_call`. Distinguish via `isinstance(e.__cause__, (httpx.TransportError, gidgethub.GitHubBroken))`.

### Abort flow

```
task raises GitHubPrimaryRateLimitError
  → stats["rate_limited"] += 1
  → pool._aborted = True
  → submit() becomes a no-op
  → __aexit__ waits for in-flight tasks
  → raises FatalError("Rate limited by GitHub API. completed: X, rate_limited: 1")
```

Same flow for network threshold breach, with message:
`"Too many network errors ({n}). completed: X, network_errors: {n}"`

---

## Acceptance Criteria

- [ ] `TaskPool` limits concurrency to `limit`
- [ ] `pool.results` contains all dicts returned by successful tasks
- [ ] `pool.stats` counts all categories correctly
- [ ] `GitHubNotFoundError` → skipped, counted, no abort
- [ ] `GitHubPrimaryRateLimitError` → immediate abort, `FatalError` raised on exit
- [ ] `GitHubSecondaryRateLimitError` → sleep + retry once; second failure → abort
- [ ] Network errors ≥ threshold → abort, `FatalError` raised on exit
- [ ] Unexpected errors → logged, counted, no abort
- [ ] In-flight tasks complete before abort raises
- [ ] `submit()` is a no-op after abort
- [ ] Clean exit logs summary at INFO
- [ ] `GitHubPrimaryRateLimitError` and `GitHubSecondaryRateLimitError` defined in `errors.py`
- [ ] `github_api_call` translates `RateLimitExceeded` → `GitHubPrimaryRateLimitError`
- [ ] `github_api_call` translates 429 → `GitHubSecondaryRateLimitError`
- [ ] `github_api_call` translates plain 403 → `GitHubNotFoundError`

---

## Contract

```json
{
  "output_files": [
    "src/ghbot/executor.py",
    "src/ghbot/errors.py",
    "src/ghbot/github/client.py",
    "tests/unit/test_executor.py",
    "tests/unit/test_client.py"
  ],
  "checks": [
    "TaskPool limits concurrency to limit",
    "results collects dicts from successful tasks",
    "stats counts completed/not_found/network_error/rate_limited/unexpected",
    "GitHubNotFoundError skipped and counted",
    "GitHubPrimaryRateLimitError aborts pool and raises FatalError",
    "GitHubSecondaryRateLimitError sleeps and retries; second failure aborts",
    "plain 403 treated as not_found",
    "network errors >= threshold aborts pool and raises FatalError",
    "unexpected errors logged and counted without abort",
    "in-flight tasks finish before abort raises",
    "submit is no-op after abort",
    "clean exit logs summary",
    "GitHubPrimaryRateLimitError and GitHubSecondaryRateLimitError are subclasses of GitHubApiError",
    "github_api_call translates RateLimitExceeded to GitHubPrimaryRateLimitError",
    "github_api_call translates 429 to GitHubSecondaryRateLimitError",
    "github_api_call translates plain 403 to GitHubNotFoundError"
  ]
}
```
