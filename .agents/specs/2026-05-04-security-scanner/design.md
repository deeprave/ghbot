# Design Document: security-scanner

## Overview

This design adds `SecurityRepoProcessor` to `processor.py`, a `print_security_report()`
function in a new `report.py` module, and refactors `__main__.py` from a single `@click.command`
to a `@click.group` with `info` and `security` subcommands. `_main` gains a `processor_cls`
parameter so the same async loop drives both processors.

No new dependencies. No changes to `TaskPool`, `Monitor`, `RepoProcessor`, `FeedbackEvent`,
`RepoResult`, or any GitHub-layer code.

---

## Architecture

```
cli() [click.group — global options]
  ├── info()   → asyncio.run(_main(cfg, InfoRepoProcessor))
  └── security() → asyncio.run(_main(cfg, SecurityRepoProcessor))
                              └── print_security_report(pool.results)

_main(cfg, processor_cls)
  └── TaskPool
        └── processor_cls(owner, repo, gh, monitor).run()
              └── _fetch_dependabot_alerts / _fetch_code_scanning_alerts / _fetch_secret_scanning_alerts
```

The `cli` group owns config merge and `configure()`. Subcommands are thin — they call
`asyncio.run(_main(...))` and handle `FatalError`. The `info` subcommand behaviour is
unchanged except it now requires an explicit `info` token on the command line.

---

## Components and Interfaces

### `__main__.py` — refactor to Click group

**Before**: single `@click.command()` named `main`.

**After**: `@click.group()` named `cli` holding all existing global options, plus two
subcommands `info` and `security`. The `_split_owners` callback and config-merge logic move
into `cli()`. `_main` gains `processor_cls`.

```python
@click.group()
@click.pass_context
@click.version_option(...)
@click.option("--owner", ...)
# ... all existing options ...
def cli(
    ctx,
    config,
    verbose,
    quiet,
    log_file,
    log_level,
    log_json,
    requests,
    owner,
    concurrency,
):
    ctx.ensure_object(dict)
    cfg = {**DEFAULTS}
    cfg.update(load_config(config))
    # ... existing merge logic ...
    configure(...)
    ctx.obj["cfg"] = cfg


@cli.command()
@click.pass_context
def info(ctx):
    cfg = ctx.obj["cfg"]
    try:
        asyncio.run(_main(cfg, InfoRepoProcessor))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)


@cli.command()
@click.pass_context
def security(ctx):
    cfg = ctx.obj["cfg"]
    try:
        asyncio.run(_main(cfg, SecurityRepoProcessor))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)
```

Running `ghbot` with no subcommand prints Click's group help and exits non-zero by
default (`invoke_without_command=False`, which is Click's default).

**`_main` signature change**:
```python
async def _main(cfg: dict, processor_cls: type) -> list[RepoResult]:
    ...
    async with TaskPool(limit=cfg["concurrency"]) as pool:
        async for owner, repo in scan_repositories(cfg["owners"], gh):
            monitor = LoggingMonitor(owner, repo["name"])
            processor = processor_cls(owner, repo["name"], gh, monitor)
            await pool.submit(processor.run)
    return pool.results
```

Returns `pool.results` so the subcommand can pass it to the report function.

---

### `SecurityRepoProcessor` (`processor.py`)

Follows the identical structure as `InfoRepoProcessor`: constructor validates owner/repo,
three `_fetch_*` helpers, outer `run()` with `FatalError` re-raise and unexpected-exception
catch.

```python
class SecurityRepoProcessor:
    def __init__(self, owner: str, repo: str, gh: object, monitor: Monitor) -> None:
        if not owner:
            raise ValueError("owner must be a non-empty string")
        if not repo:
            raise ValueError("repo must be a non-empty string")
        self._owner = owner
        self._repo = repo
        self._gh = gh
        self._monitor = monitor

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

    async def run(self) -> RepoResult: ...
```

#### Data points

| Key | Endpoint | Default on 403/404 | Default on error |
|---|---|---|---|
| `dependabot_alerts` | `GET /repos/{owner}/{repo}/dependabot/alerts?state=open` | `None` | `None` |
| `code_scanning_alerts` | `GET /repos/{owner}/{repo}/code-scanning/alerts?state=open` | `None` | `None` |
| `secret_scanning_alerts` | `GET /repos/{owner}/{repo}/secret-scanning/alerts?state=open` | `None` | `None` |

All three use `getiter` and count the yielded items. `None` means no access; `0` means
accessible but no open alerts.

#### Per-step pattern

```python
async def _fetch_dependabot_alerts(self, result: RepoResult) -> None:
    await self._monitor.send_event(
        FeedbackEvent("progress", "debug", "fetching dependabot alerts")
    )
    try:
        async with github_api_call(self._gh):
            count = sum(
                1
                async for _ in self._gh.getiter(
                    "/repos/{owner}/{repo}/dependabot/alerts",
                    url_vars={"owner": self._owner, "repo": self._repo},
                    iterable_key=None,
                    extra_headers={
                        "state": "open"
                    },  # passed as query param via url_vars
                )
            )
        result.results["dependabot_alerts"] = count
    except GitHubNotFoundError:
        await self._monitor.send_event(
            FeedbackEvent("fetch", "debug", "dependabot alerts not accessible")
        )
        result.results["dependabot_alerts"] = None
    except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
        raise
    except GitHubApiError as e:
        await self._monitor.send_event(
            FeedbackEvent("fetch", "error", f"failed to fetch dependabot alerts: {e}")
        )
        result.results["dependabot_alerts"] = None
        result.errors.append(f"dependabot alerts: {e}")
```

**Query parameter note**: `gidgethub.getiter` accepts query params embedded in the URL
string. The `state=open` filter is appended directly to the URL template:
`"/repos/{owner}/{repo}/dependabot/alerts?state=open"`.

#### `run()` structure

Identical to `InfoRepoProcessor.run()`:
- Emit `FeedbackEvent("progress", "info", "processing started")`
- Call all three `_fetch_*` methods inside a `try` block
- Re-raise `FatalError` subclasses
- Catch unexpected exceptions → `status = "failed"`
- Set `status = "partial"` if `result.errors` is non-empty after the `else` branch
- Emit `FeedbackEvent("progress", "debug", "processing finished")`
- Return `result`

---

### `report.py` — new module

```python
# src/ghbot/report.py

from ghbot.processor import RepoResult


def print_security_report(results: list[RepoResult]) -> None: ...
```

#### Summary calculation

```python
scanned = len(results)
repos_with_issues = sum(
    1
    for r in results
    if any(
        v not in (None, 0)
        for v in [
            r.results.get("dependabot_alerts"),
            r.results.get("code_scanning_alerts"),
            r.results.get("secret_scanning_alerts"),
        ]
    )
)
```

For each alert type, sum across all results, treating `None` as 0 for the total. If *all*
repos returned `None` for a given type, display `"N/A"` instead of `0`.

```python
def _total(results, key):
    values = [r.results.get(key) for r in results]
    if all(v is None for v in values):
        return "N/A"
    return sum(v for v in values if v is not None)
```

#### Output format

```
Repos scanned:           42
Repos with issues:       12
Dependabot alerts:       34
Code scanning alerts:     8
Secret scanning alerts:   3

owner/repo-name
  Dependabot alerts:       5
  Code scanning alerts:    2
  Secret scanning alerts:  0
```

Column width: label left-aligned, value right-aligned at column 30. Per-repo section
separated by a blank line. Repos sorted by `owner/repo` name. Only repos with at least one
non-None, non-zero count appear in the per-repo section.

---

## Error Handling

`SecurityRepoProcessor` error handling is identical to `InfoRepoProcessor`:

| Condition | Handling | Status impact |
|---|---|---|
| `GitHubNotFoundError` (403/404) | set `None`, emit debug event, continue | none (not an error) |
| `GitHubApiError` | set `None`, emit error event, append to `errors` | `"partial"` |
| Unexpected exception | emit error event, set `"failed"`, return | `"failed"` |
| `FatalError` subclass | re-raise | N/A |

---

## Testing Strategy

### `tests/unit/test_security_processor.py`

- Constructor: empty owner/repo raises `ValueError`
- `isinstance(processor, RepoProcessor)` passes
- Happy path: all three endpoints return items → counts stored, status `"success"`
- 403/404 on each endpoint → `None` count, debug event, no error, status `"success"`
- `GitHubApiError` on one endpoint → `None` count, error recorded, status `"partial"`
- `FatalError` subclasses re-raised from `run()`
- Unexpected exception → status `"failed"`, error recorded, result returned

### `tests/unit/test_report.py`

- All repos have alerts → correct totals, per-repo section present
- No repos have issues → per-repo section absent
- All repos returned `None` for a type → that type shows `"N/A"`
- Mix of `None` and int counts → `None` excluded from sum, `"N/A"` not shown
- Empty results list → `"Repos scanned: 0"`, no per-repo section
- Output goes to stdout (capture with `capsys`)

### `tests/unit/test_main.py` — updates

- `ghbot` with no subcommand → exit code non-zero
- `ghbot info` → `_main` called with `InfoRepoProcessor`
- `ghbot security` → `_main` called with `SecurityRepoProcessor`
- `ghbot security` → `print_security_report` called with `pool.results`
- `ghbot info` → `print_security_report` not called
- Global options (`--owner`, `--concurrency`, etc.) still work with both subcommands

### Mocking strategy

- Patch `ghbot.processor.github_api_call` for processor tests
- Use `RecordingMonitor` stub (same pattern as `InfoRepoProcessor` tests)
- Use `capsys` for report output assertions
- Patch `ghbot.__main__._main` for CLI routing tests
- Patch `ghbot.__main__.print_security_report` to verify call/no-call
