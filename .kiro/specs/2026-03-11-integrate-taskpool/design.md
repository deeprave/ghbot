# Design: Integrate TaskPool

## Architecture Overview

This spec wires three already-implemented components together:

```
main() [sync, click]
  └── _main(cfg) [async]
        ├── scan_repositories(cfg["owners"], gh)  → yields (owner, repo)
        └── TaskPool(limit=cfg["concurrency"])
              └── process_repo(owner, repo, gh)   → dict per repo
```

The change is additive: `_main` gains a `TaskPool` context manager wrapping the existing
`scan_repositories` loop, and `process_repo` is added to `repos.py` as the task unit.
Config and CLI gain one new key: `concurrency`.

---

## Component Breakdown

### `src/ghbot/github/repos.py` — add `process_repo`

New async function alongside existing `list_repos` / `scan_repositories`:

```python
async def process_repo(owner: str, repo: dict, gh: GitHubAPI) -> dict:
    log.debug("processing %s/%s", owner, repo["name"])
    return {"owner": owner, "repo": repo["name"]}
```

No changes to `list_repos` or `scan_repositories`.

### `src/ghbot/__main__.py` — wire TaskPool into `_main`

Replace the bare `async for` loop with a `TaskPool` context manager:

```python
async def _main(cfg: dict) -> None:
    log.info("ghbot starting")
    token = await get_auth_token()
    async with httpx.AsyncClient() as client:
        gh = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        async with TaskPool(limit=cfg["concurrency"]) as pool:
            async for owner, repo in scan_repositories(cfg["owners"], gh):
                await pool.submit(process_repo, owner, repo, gh)
    log.info("stats: %s", pool.stats)
```

Add imports: `TaskPool` from `ghbot.executor`, `process_repo` from `ghbot.github.repos`.
Add `--concurrency` CLI flag and merge it into `cfg`.

### `src/ghbot/config.py` — add `concurrency` to DEFAULTS

```python
DEFAULTS: dict[str, Any] = {
    "owners": [],
    "log-file": None,
    "log-json": False,
    "log-level": "info",
    "concurrency": 16,   # new
}
```

No other changes to `load_config`.

---

## Data Models

No new data models. Existing types:

| Name | Type | Source |
|---|---|---|
| `cfg` | `dict[str, Any]` | merged in `main()` |
| `cfg["concurrency"]` | `int` | new key, default 16 |
| `pool.results` | `list[dict]` | `TaskPool` |
| `pool.stats` | `dict[str, int]` | `TaskPool` |
| `process_repo` return | `dict` | `{"owner": str, "repo": str}` |

---

## API Contracts

### `process_repo(owner, repo, gh) -> dict`
- Input: `owner: str`, `repo: dict` (must have `"name"` key), `gh: GitHubAPI`
- Output: `{"owner": owner, "repo": repo["name"]}`
- Raises: nothing (stub); future implementations may raise `GitHubApiError`

### `--concurrency` CLI flag
- Type: `int`, default `None` (not `16` — `None` signals "not provided by CLI")
- Merged into `cfg["concurrency"]` only when not `None`
- `DEFAULTS["concurrency"] = 16` provides the fallback

### Config file key
```toml
concurrency = 8   # int, optional
```

---

## Dependency Mapping

```
__main__.py
  imports: TaskPool (executor.py)          ← new import
  imports: process_repo (github/repos.py)  ← new import
  imports: scan_repositories (github/repos.py)  ← existing

github/repos.py
  adds: process_repo                        ← new function
  no new imports needed

config.py
  DEFAULTS gains "concurrency": 16         ← one-line change
```

No new third-party dependencies.

---

## Technical Decisions

1. **`pool.stats` logged after `async with` block exits** — `TaskPool.__aexit__` raises
   `FatalError` on abort, so `log.info("stats: %s", pool.stats)` must be outside the
   `async with` block to run on clean exit only. On abort, the `FatalError` propagates to
   `main()`'s catch block — stats are embedded in the abort message by `TaskPool` itself.

2. **`--concurrency` default is `None` in click, not `16`** — using `default=None` lets
   `main()` distinguish "user passed a value" from "user didn't pass anything", enabling
   the correct merge: `if concurrency is not None: cfg["concurrency"] = concurrency`.
   The `16` default lives only in `DEFAULTS`.

3. **`process_repo` in `repos.py`, not `__main__.py`** — keeps all GitHub-layer functions
   together. `__main__.py` imports it; `TaskPool` never imports from the GitHub layer.

4. **No change to `scan_repositories` or `list_repos`** — they already have the right
   signatures and behaviour. The integration is purely at the `_main` call site.

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| `pool.stats` accessed after `FatalError` abort | Low | `stats` is logged by `TaskPool` in the abort message; `_main`'s `log.info` is outside the `async with` block so it only runs on clean exit |
| `process_repo` called with repo dict missing `"name"` | Low | GitHub API always returns `"name"`; `list_repos` yields raw API dicts unchanged |
| `concurrency` config key conflicts with existing TOML | None | Key is new; no existing config files use it |
| Test isolation: `_main` tests need `TaskPool` patched | Low | Existing test pattern (patch at import site) applies directly |
