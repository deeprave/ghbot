# Spec Lite: Task Executor

## Problem
Process many repositories concurrently without overwhelming the GitHub API. A bounded pool runs up to N coroutines, collects results, and applies an intelligent error policy.

## Interface
```python
async with TaskPool(limit=16) as pool:
    async for owner, repo in scan_repositories(cfg["owners"], gh):
        await pool.submit(process_repo, owner, repo, gh)
# pool.results: list[dict]  — one dict per successful task
# pool.stats: dict          — counts by category
```

## Error Policy (per task, no cancel-all)
| Exception | Action |
|---|---|
| `GitHubNotFoundError` | count `not_found`, skip |
| `GitHubPrimaryRateLimitError` (gidgethub `RateLimitExceeded`, 403) | count `rate_limited`, abort immediately |
| `GitHubSecondaryRateLimitError` (429) | count `rate_limited`, sleep `Retry-After`, retry once; second failure → abort |
| `GitHubApiError` with network cause | count `network_error`; if ≥ 3 → abort |
| plain 403 (access denied) | mapped to `GitHubNotFoundError` in `github_api_call` |
| anything else | count `unexpected`, log error, skip |

"Abort" = stop accepting submits, wait for in-flight tasks, raise `FatalError` with summary.

## Stats keys
`completed`, `not_found`, `network_error`, `rate_limited`, `unexpected`

## Network error classification
`isinstance(e.__cause__, (httpx.TransportError, gidgethub.GitHubBroken))`

## New error classes
```python
class GitHubPrimaryRateLimitError(GitHubApiError): ...  # errors.py


class GitHubSecondaryRateLimitError(GitHubApiError): ...  # errors.py
```

## github_api_call exception mapping
| Exception | Condition | Raises |
|---|---|---|
| `gidgethub.RateLimitExceeded` | — | `GitHubPrimaryRateLimitError` |
| `gidgethub.HTTPException` | 429 | `GitHubSecondaryRateLimitError` |
| `gidgethub.HTTPException` | 403 plain | `GitHubNotFoundError` |
| `gidgethub.HTTPException` | 404 | `GitHubNotFoundError` |
| `gidgethub.HTTPException` | other | `GitHubApiError` |
| transport/broken | — | sleep 1s → `GitHubApiError` |

Note: `RateLimitExceeded` caught before `HTTPException` (it's a subclass).

## Rules
- Tasks are independent — wrapping prevents TaskGroup cancel-all
- `submit()` is no-op after abort
- Pool not reusable after exit
- Clean exit logs INFO summary: `"completed: {n}, not_found: {n}, network_errors: {n}"`

## Output Files
- `src/ghbot/executor.py`
- `src/ghbot/errors.py`
- `src/ghbot/github/client.py`
- `tests/unit/test_executor.py`
- `tests/unit/test_client.py`
