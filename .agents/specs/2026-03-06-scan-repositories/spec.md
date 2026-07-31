# Spec: Scan Repositories

## Problem / Context

ghbot needs a startup task that discovers all repositories for each configured owner and
streams them to the caller for further processing. This spec covers discovery and progress
logging only — per-repository task fan-out is deferred to the next spec.

It also establishes the config-as-single-source-of-truth pattern: all runtime settings
(owners, logging, etc.) are resolved once in `main()` by merging defaults → config file →
CLI overrides, then passed as a single `cfg` dict into `_main(cfg)`.

---

## Requirements

### Functional

1. `github_api_call(gh)` is an async context manager in `src/ghbot/github/client.py` that wraps GitHub API calls and translates exceptions to domain errors
2. `list_repos(owner, gh)` is an async generator in `src/ghbot/github/repos.py` that yields repo dicts for all pages
3. `scan_repositories(owners, gh)` is an async generator that iterates over all owners and yields `(owner, repo)` tuples
4. `scan_repositories` logs a warning and yields nothing when `owners` is empty
5. `_main(cfg)` creates an `httpx.AsyncClient` and `GitHubAPI` instance once, reads `cfg["owners"]`, calls `scan_repositories`, and logs `<owner>/<repo>` at DEBUG level for each result
6. `main()` builds a merged config dict (defaults → config file → CLI overrides) and passes it as `cfg` to `_main(cfg)` — CLI flags always win
7. Config file supports keys: `owners` (comma-separated string), `log-file` (str), `log-json` (bool), `log-level` (str)
8. `list_repos` retries once on `GitHubApiError`; on second failure logs the error and skips the owner — does not propagate
9. `UnexpectedError(FatalError)` exists in `errors.py` for exceptions that are not explicitly handled

### Non-functional

- All GitHub API calls go through `src/ghbot/github/` — never inline in `_main()`
- Auth token retrieved via `get_auth_token()` — lazy, not at startup
- `httpx.AsyncClient` is owned by the caller and injected — never created inside individual API functions
- `cfg` is the single source of truth for all runtime settings — no separate params alongside it

---

## Constraints

- GitHub API via `gidgethub` + `httpx.AsyncClient` (already in dependencies)
- Pagination: must handle paginated responses from GitHub's list-repos endpoint
- `owners` sourced from `--owner` CLI flags or config file; if neither provides owners, log a warning and exit cleanly

---

## Config File Format

```toml
owners = "owner1,owner2"
log-json = true
log-file = "/tmp/ghbot.log"
log-level = "debug"
```

### Merge Precedence (highest → lowest)
1. CLI flags
2. Config file values
3. Built-in defaults

`main()` applies this merge once and passes the result as `cfg` to `_main(cfg)`.

---

## High-level Design

```
src/ghbot/github/
├── client.py      # github_api_call(gh) → async context manager
├── repos.py       # list_repos(owner, gh) → AsyncGenerator[dict]
                   # scan_repositories(owners, gh) → AsyncGenerator[tuple[str, dict]]
src/ghbot/
├── errors.py      # GitHubApiError, GitHubNotFoundError, UnexpectedError
├── config.py      # load_config(), DEFAULTS
```

### Error Classes

```python
class GitHubApiError(FatalError): ...


class GitHubNotFoundError(GitHubApiError): ...


class UnexpectedError(FatalError): ...
```

### `github_api_call` context manager

Wraps any GitHub API call. Translates exceptions:

| Exception | Behaviour |
|---|---|
| `gidgethub.HTTPException` with 404 | raises `GitHubNotFoundError` |
| other `gidgethub.HTTPException` | raises `GitHubApiError` |
| `gidgethub.GitHubBroken` / `httpx.TransportError` | sleep 1s then raise `GitHubApiError` |

Sleep-before-raise lives here. Callers that want to retry wrap the call in a loop.

### API endpoint
`GET /users/{owner}/repos` with `type=all` — fetches all repo types (public, private, forks, sources). Use `gidgethub` + `httpx.AsyncClient` via `getiter`.

### Flow
```
main()
  cfg = merge(DEFAULTS, load_config(), cli_flags)
  _main(cfg)

_main(cfg)
  async with httpx.AsyncClient() as client:
    gh = GitHubAPI(client, "ghbot", oauth_token=token)
    async for owner, repo in scan_repositories(cfg["owners"], gh):
      log.debug("%s/%s", owner, repo["name"])
```

### Config merge in `main()`
```python
cfg = {**DEFAULTS}
cfg.update(load_config(config_path))  # config file overlays defaults
if owners:
    cfg["owners"] = list(owners)  # CLI overlays config file
if log_file:
    cfg["log-file"] = log_file
if log_json:
    cfg["log-json"] = log_json
# ... etc for each CLI flag that has a config equivalent
```

### scan_repositories signature
```python
async def scan_repositories(
    owners: Sequence[str], gh: GitHubAPI
) -> AsyncGenerator[tuple[str, dict], None]:
    if not owners:
        log.warning("No owners specified")
        return
    for owner in owners:
        async for repo in list_repos(owner, gh):
            yield owner, repo
```

### list_repos signature (with retry)
```python
async def list_repos(owner: str, gh: GitHubAPI) -> AsyncGenerator[dict, None]:
    for attempt in range(2):
        try:
            async with github_api_call(gh):
                async for repo in gh.getiter(
                    f"/users/{owner}/repos", url_vars={"type": "all"}
                ):
                    yield repo
            return
        except GitHubNotFoundError:
            log.warning("Owner not found, skipping: %s", owner)
            return
        except GitHubApiError as e:
            if attempt == 1:
                log.error("GitHub API error for %s, skipping: %s", owner, e)
                return
```

---

## Acceptance Criteria

- [x] `list_repos(owner, gh)` yields repo dicts for all pages
- [x] `scan_repositories` yields `(owner, repo)` tuples for each repository
- [x] `_main()` logs `<owner>/<repo>` at DEBUG for each yielded tuple
- [x] `_main()` creates `httpx.AsyncClient` and `GitHubAPI` once and passes `gh` to `scan_repositories`
- [x] No owners → logs warning, returns without error
- [x] `github_api_call(gh)` translates 404 → `GitHubNotFoundError`
- [x] `github_api_call(gh)` translates other HTTP errors → `GitHubApiError`
- [x] `github_api_call(gh)` sleeps 1s on `GitHubBroken`/`TransportError` then raises `GitHubApiError`
- [x] `list_repos` catches `GitHubNotFoundError` and logs warning + skips
- [x] `_main()` passes `GitHubAPI` instance (not token) to `scan_repositories`
- [ ] `list_repos` retries once on `GitHubApiError`; second failure logs error + skips owner
- [ ] `UnexpectedError(FatalError)` defined in `errors.py`
- [ ] `main()` builds merged config dict (defaults → config file → CLI) and passes to `_main(cfg)`
- [ ] `_main(cfg)` accepts single `cfg` dict; reads `cfg["owners"]` — no separate `owners` param
- [ ] Config file keys `owners`, `log-file`, `log-json`, `log-level` are recognised and merged
- [ ] `scan_repositories` and `list_repos` accept `Sequence[str]` for owners
- [ ] `list_repos` passes `type=all` to GitHub API

---

## Contract

```json
{
  "output_files": [
    "src/ghbot/github/client.py",
    "src/ghbot/github/repos.py",
    "src/ghbot/__main__.py",
    "src/ghbot/errors.py",
    "src/ghbot/config.py",
    "tests/unit/test_client.py",
    "tests/unit/test_repos.py",
    "tests/unit/test_main.py"
  ],
  "checks": [
    "github_api_call translates 404 to GitHubNotFoundError",
    "github_api_call translates other HTTP errors to GitHubApiError",
    "github_api_call sleeps 1s on transport/broken errors then raises GitHubApiError",
    "list_repos yields repo dicts from paginated GitHub API with type=all",
    "list_repos catches GitHubNotFoundError and warns + skips",
    "list_repos retries once on GitHubApiError then logs error + skips",
    "scan_repositories yields (owner, repo) tuples",
    "scan_repositories and list_repos accept Sequence[str]",
    "_main(cfg) reads owners from cfg",
    "_main creates httpx.AsyncClient and GitHubAPI once",
    "_main logs owner/repo at debug for each repository",
    "no owners logs a warning and returns cleanly",
    "main() merges defaults + config file + CLI into cfg",
    "CLI flags override config file values override defaults",
    "config file owners/log-file/log-json/log-level keys are recognised",
    "UnexpectedError is a subclass of FatalError"
  ]
}
```
