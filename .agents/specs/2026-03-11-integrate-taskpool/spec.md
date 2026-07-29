# Spec: Integrate TaskPool

## Problem / Context

`TaskPool` and `scan_repositories` exist independently. `_main(cfg)` currently only logs
`owner/repo` at DEBUG — it never fans out work. This spec wires them together: for each
discovered repository, `_main` submits a `process_repo` task to the pool, which runs
concurrently up to the configured limit and collects results.

It also introduces `process_repo` as the per-repository work unit and adds `--concurrency`
as a CLI flag / config key so operators can tune the pool size.

---

## Requirements

### Functional

1. `process_repo(owner: str, repo: dict, gh: GitHubAPI) -> dict` is an async function in
   `src/ghbot/github/repos.py` — the unit of work submitted to the pool. For now it
   returns `{"owner": owner, "repo": repo["name"]}` (stub; real logic deferred).
2. `_main(cfg)` creates a `TaskPool(limit=cfg["concurrency"])` and, for each
   `(owner, repo)` yielded by `scan_repositories`, calls `await pool.submit(process_repo, owner, repo, gh)`.
3. After the pool exits, `_main` logs `pool.stats` at INFO.
4. `--concurrency` CLI flag (int, default 16) maps to `cfg["concurrency"]`.
5. Config file supports `concurrency` key (int).
6. `DEFAULTS` in `config.py` includes `"concurrency": 16`.
7. `main()` merges `concurrency` from config file and CLI flag into `cfg` using the same
   precedence pattern (CLI > config file > defaults).

### Non-functional

- `process_repo` is the only function submitted to the pool — no inline lambdas in `_main`.
- `TaskPool` is used as an async context manager wrapping the `scan_repositories` loop.
- `gh` instance is created once in `_main` and passed to both `scan_repositories` and `process_repo`.

---

## Constraints

- No new dependencies.
- `process_repo` lives in `src/ghbot/github/repos.py` alongside `list_repos` and
  `scan_repositories` — it is a GitHub-layer function.
- `TaskPool` import in `__main__.py` — not in the GitHub layer.

---

## Config File Format (addition)

```toml
concurrency = 8
```

Merge precedence: CLI `--concurrency` > config file `concurrency` > default (16).

---

## High-level Design

```
_main(cfg)
  token = await get_auth_token()
  async with httpx.AsyncClient() as client:
    gh = GitHubAPI(client, "ghbot", oauth_token=token)
    async with TaskPool(limit=cfg["concurrency"]) as pool:
      async for owner, repo in scan_repositories(cfg["owners"], gh):
        await pool.submit(process_repo, owner, repo, gh)
  log.info("stats: %s", pool.stats)
```

### `process_repo` stub

```python
async def process_repo(owner: str, repo: dict, gh: GitHubAPI) -> dict:
    log.debug("processing %s/%s", owner, repo["name"])
    return {"owner": owner, "repo": repo["name"]}
```

### Config merge addition in `main()`

```python
if concurrency is not None:
    cfg["concurrency"] = concurrency
```

---

## Acceptance Criteria

- [ ] `process_repo(owner, repo, gh)` exists in `repos.py` and returns a dict
- [ ] `_main(cfg)` submits `process_repo` to `TaskPool` for each repo
- [ ] `TaskPool` is created with `limit=cfg["concurrency"]`
- [ ] `_main` logs `pool.stats` at INFO after pool exits
- [ ] `--concurrency` CLI flag sets `cfg["concurrency"]`
- [ ] Config file `concurrency` key is recognised and merged
- [ ] `DEFAULTS["concurrency"]` is `16`
- [ ] CLI `--concurrency` overrides config file value overrides default

---

## Contract

```json
{
  "output_files": [
    "src/ghbot/github/repos.py",
    "src/ghbot/__main__.py",
    "src/ghbot/config.py",
    "tests/unit/test_main.py",
    "tests/unit/test_repos.py"
  ],
  "checks": [
    "process_repo returns dict with owner and repo name",
    "_main submits process_repo to TaskPool for each (owner, repo)",
    "TaskPool created with limit from cfg[concurrency]",
    "_main logs pool.stats at INFO after pool exits",
    "--concurrency CLI flag maps to cfg[concurrency]",
    "config file concurrency key is merged into cfg",
    "DEFAULTS includes concurrency=16",
    "CLI concurrency overrides config file overrides default"
  ]
}
```
