# Spec Lite: Scan Repositories

## Problem
On startup, ghbot discovers all repositories for each configured owner and streams them
to `_main(cfg)` for logging. Also establishes config-as-single-source-of-truth: all runtime
settings resolved once in `main()` and passed as a single `cfg` dict.

## Flow
```
main()
  cfg = merge(DEFAULTS, load_config(), cli_flags)  # CLI wins
  _main(cfg)

_main(cfg)
  async with httpx.AsyncClient() as client:
    gh = GitHubAPI(client, "ghbot", oauth_token=token)
    async for owner, repo in scan_repositories(cfg["owners"], gh):
      log.debug("%s/%s", owner, repo["name"])
```

## Key Requirements
1. `github_api_call(gh)` — async context manager in `github/client.py`; translates exceptions: 404 → `GitHubNotFoundError`, other HTTP → `GitHubApiError`, transport/broken → sleep 1s + raise `GitHubApiError`
2. `list_repos(owner, gh)` — async generator, paginates via `getiter` with `type=all`; retries once on `GitHubApiError`; second failure logs error + skips owner; catches `GitHubNotFoundError` → warn + skip
3. `scan_repositories(owners, gh)` — async generator yielding `(owner, repo)` tuples; both accept `Sequence[str]`
4. No owners → log warning, return cleanly
5. `_main(cfg)` — single `cfg` param; reads `cfg["owners"]`; creates `httpx.AsyncClient` + `GitHubAPI` once
6. `main()` — merges DEFAULTS → config file → CLI flags into `cfg`; passes to `_main(cfg)`

## Config File Format
```toml
owners = "owner1,owner2"
log-json = true
log-file = "/tmp/ghbot.log"
log-level = "debug"
```
Merge precedence: CLI > config file > defaults.

## Error Classes (`errors.py`)
- `GitHubApiError(FatalError)` — known API/transport failure; non-fatal in `list_repos` (logged + skipped)
- `GitHubNotFoundError(GitHubApiError)` — 404; warn + skip
- `UnexpectedError(FatalError)` — unhandled exceptions; fatal, propagates to `main()`

## Rules
- All GitHub API calls in `src/ghbot/github/` — never inline in `_main()`
- Token retrieved lazily via `get_auth_token()` — not at startup
- `httpx.AsyncClient` owned by caller, injected — never created inside API functions
- `cfg` is single source of truth — no separate params alongside it

## Output Files
- `src/ghbot/github/client.py`
- `src/ghbot/github/repos.py`
- `src/ghbot/__main__.py`
- `src/ghbot/errors.py`
- `src/ghbot/config.py`
- `tests/unit/test_client.py`
- `tests/unit/test_repos.py`
- `tests/unit/test_main.py`
