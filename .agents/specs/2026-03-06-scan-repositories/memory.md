# Memory: Scan Repositories

## Key Decisions

- `cfg` is the single source of truth: `main()` merges `DEFAULTS → load_config() → CLI flags` once and passes the result as a plain `dict` to `_main(cfg)`. No separate params alongside `cfg`.
- `owners` in the config file is a comma-separated string (`"owner1,owner2"`); splitting happens in `main()` when CLI flags are absent, not in `load_config()`. This keeps `load_config()` a pure TOML reader.
- `list_repos` retry loop uses `for attempt in range(2)` — simple, no retry library. On attempt 0 failure it loops; on attempt 1 failure it logs and returns. `GitHubNotFoundError` short-circuits immediately on either attempt.
- `github_api_call` is an `@asynccontextmanager` that wraps the `yield` in a try/except. Sleep-before-raise for transport errors lives here — callers that want retry wrap the whole call in a loop.
- `GitHubApiError` is a subclass of `FatalError` but is treated as non-fatal inside `list_repos` (logged + skipped). The class hierarchy reflects severity at the API layer; handling policy lives in the caller.
- `UnexpectedError(FatalError)` added as a named class for unhandled exceptions — gives future callers a distinct type to catch without changing the base `FatalError` interface.
- `load_config` merges TOML values on top of `DEFAULTS` before returning — callers always get a complete dict, never a partial one.

## Patterns Used

### Async generator retry with `range(2)`
```python
for attempt in range(2):
    try:
        async with github_api_call(gh):
            async for item in gh.getiter(...):
                yield item
        return
    except RecoverableError as e:
        if attempt == 1:
            log.error(...)
            return
        # attempt 0: fall through to retry
```
Clean, no state variables, no `while True`. The `return` after the happy path exits the generator.

### Async generator stub for testing
```python
async def _stub(owner, gh):
    yield {"name": "alpha"}


with patch("ghbot.github.repos.list_repos", side_effect=_stub):
    result = [(o, r) async for o, r in scan_repositories(["org"], gh)]
```
`side_effect` on a patch accepts an async generator function directly — no `AsyncMock` needed.

### `getiter` mock with plain async def
```python
async def _getiter(url, url_vars=None):
    yield {"name": "repo1"}


gh = AsyncMock()
gh.getiter = _getiter
```
Assigning a real async generator function to the mock attribute is simpler than configuring `AsyncMock` to return an async iterator.

### Retry test via `getiter` call count
```python
call_count = 0


async def _getiter(url, url_vars=None):
    nonlocal call_count
    call_count += 1
    if call_count == 1:
        raise GitHubApiError("api error")
    yield {"name": "repo1"}


gh.getiter = _getiter
result = [r async for r in list_repos("owner1", gh)]
assert call_count == 2
```
Raising inside the async generator function (not via `AsyncMock.side_effect`) is the most natural way to simulate per-call failures.

### Config merge in `main()`
```python
cfg = {**DEFAULTS}
cfg.update(load_config(config_path))  # file overlays defaults
if owner:
    cfg["owners"] = list(owner)  # CLI overlays file
elif isinstance(cfg.get("owners"), str):
    cfg["owners"] = [o for o in cfg["owners"].split(",") if o]
if log_file:
    cfg["log-file"] = log_file
```
Each CLI flag only overwrites `cfg` if it was explicitly provided (truthy check). String-to-list normalisation for `owners` happens here, not in `load_config`.

### `_split_owners` click callback
```python
def _split_owners(ctx, param, value: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(o for v in value for o in v.split(",") if o)
```
Handles both `--owner a,b` and repeated `--owner a --owner b` uniformly before the value reaches `main()`.

## Lessons Learned

- **`load_config` returns raw TOML values**: `owners` stays as a string in the returned dict. Callers (i.e. `main()`) are responsible for splitting. This keeps `load_config` simple and avoids encoding CLI-specific logic in the config layer.
- **`load_config` merges on top of DEFAULTS**: returning `{**DEFAULTS, **toml_data}` means callers always get a complete dict — no `KeyError` on missing keys.
- **`github_api_call` exception order matters**: `gidgethub.RateLimitExceeded` is a subclass of `HTTPException` — it must be caught first. Transport errors (`_RETRYABLE` tuple) are caught before both.
- **Named tuple for exception groups**: `_RETRYABLE = (gidgethub.GitHubBroken, httpx.TransportError)` at module level makes the `except _RETRYABLE` clause self-documenting and easy to extend.
- **`caplog.at_level` is required**: without it, the logger level may be too high to capture expected records. Always use `with caplog.at_level(logging.WARNING):` in log-assertion tests.
- **`_main` test patches at import site**: patch `ghbot.__main__.scan_repositories`, not `ghbot.github.repos.scan_repositories`, to intercept the call as seen by `_main`.
- **`MagicMock(spec=GitHubAPI)` for the gh instance**: using `spec=` catches attribute typos at test time without needing a real API client.

## Follow-ups

- `owners` string-splitting in `main()` is duplicated logic (split on comma, strip empty). Extract a `_parse_owners(raw: str) -> list[str]` helper if a third call site appears.
- `load_config` silently returns `DEFAULTS` for a missing explicit `--config` path. Consider logging a debug message when the config file is not found, to aid troubleshooting.
- `_main` currently only logs `owner/repo` at DEBUG — the next spec (task-executor) will fan out work here. The `scan_repositories` call site in `_main` is the natural injection point.
- `log-level` from config file is read in `main()` but the CLI `--log-level` flag is not merged into `cfg` (only `log-file` and `log-json` are). This is a latent inconsistency — `cfg["log-level"]` falls back to the config file value, ignoring the CLI flag unless explicitly wired.
