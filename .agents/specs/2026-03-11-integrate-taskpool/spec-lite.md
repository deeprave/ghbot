# Spec Lite: Integrate TaskPool

## Problem
`_main(cfg)` only logs `owner/repo` at DEBUG. Wire `TaskPool` and `scan_repositories` together so each discovered repo is processed concurrently via `process_repo`.

## Flow
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

## Key Requirements
1. `process_repo(owner, repo, gh) -> dict` in `repos.py` — stub returning `{"owner": owner, "repo": repo["name"]}`
2. `_main(cfg)` wraps the scan loop in `TaskPool(limit=cfg["concurrency"])`; submits `process_repo` for each repo
3. `_main` logs `pool.stats` at INFO after pool exits
4. `--concurrency` CLI flag (int) maps to `cfg["concurrency"]`
5. Config file `concurrency` key (int) is recognised and merged
6. `DEFAULTS["concurrency"] = 16`
7. Merge precedence: CLI `--concurrency` > config file > default (16)

## Config File Addition
```toml
concurrency = 8
```

## Rules
- `process_repo` is the only function submitted to the pool — no inline lambdas
- `TaskPool` imported in `__main__.py` only — not in the GitHub layer
- `gh` created once in `_main`, passed to both `scan_repositories` and `process_repo`

## Output Files
- `src/ghbot/github/repos.py`
- `src/ghbot/__main__.py`
- `src/ghbot/config.py`
- `tests/unit/test_main.py`
- `tests/unit/test_repos.py`
