# Tasks: Task Executor

## Task 1: Rate limit error classes + client.py translation
- [x] 1.1 Add `GitHubPrimaryRateLimitError` and `GitHubSecondaryRateLimitError` to `src/ghbot/errors.py`
- [x] 1.2 Add tests in `tests/unit/test_client.py`: `RateLimitExceeded` → `GitHubPrimaryRateLimitError`; 429 → `GitHubSecondaryRateLimitError`; plain 403 → `GitHubNotFoundError`
- [x] 1.3 Update `github_api_call` in `src/ghbot/github/client.py` with full exception mapping

## Task 2: TaskPool — concurrency and result collection
- [x] 2.1 Add tests in `tests/unit/test_executor.py`: concurrency limited to `limit`; `pool.results` collects all returned dicts
- [x] 2.2 Implement `TaskPool` in `src/ghbot/executor.py` with `asyncio.Semaphore`; collect results

## Task 3: TaskPool — error policy
- [x] 3.1 Add tests: `GitHubNotFoundError` → counted, skipped; `GitHubPrimaryRateLimitError` → abort + `FatalError`; `GitHubSecondaryRateLimitError` → sleep + retry; network errors ≥ 3 → abort; unexpected → logged + counted
- [x] 3.2 Implement error policy in `TaskPool._handle_error`

## Task 4: TaskPool — abort and exit behaviour
- [x] 4.1 Add tests: `submit()` is no-op after abort; in-flight tasks finish before `FatalError` raised; clean exit logs INFO summary
- [x] 4.2 Implement abort flow in `__aexit__`
