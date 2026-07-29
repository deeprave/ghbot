# Spec: Security Scanner

## Problem / Context

ghbot currently has no way to surface GitHub's built-in security and code quality findings.
The GitHub UI exposes these under the "Security" tab: Dependabot vulnerability alerts, code
scanning alerts, and secret scanning alerts. Operators managing many repositories need a
single command that scans all repos for a given owner and reports open findings — overall
totals and a per-repo breakdown for any repo that has issues.

This spec also introduces subcommand-based dispatch so that different processor types can be
invoked explicitly:

```
ghbot --owner <name> info      # InfoRepoProcessor
ghbot --owner <name> security  # SecurityRepoProcessor
ghbot --owner <name>           # error: must specify a command
```

---

## Requirements

### Functional

1. A `security` subcommand is added to the CLI. Running `ghbot` without a subcommand
   prints an error and exits non-zero.
2. `ghbot --owner <name> info` runs `InfoRepoProcessor` (existing behaviour, now explicit).
3. `ghbot --owner <name> security` runs `SecurityRepoProcessor` for each discovered repo.
4. `SecurityRepoProcessor` collects three data points per repo via the GitHub API:
   - `dependabot_alerts` — open Dependabot vulnerability alerts
     (`GET /repos/{owner}/{repo}/dependabot/alerts?state=open`)
   - `code_scanning_alerts` — open code scanning alerts
     (`GET /repos/{owner}/{repo}/code-scanning/alerts?state=open`)
   - `secret_scanning_alerts` — open secret scanning alerts
     (`GET /repos/{owner}/{repo}/secret-scanning/alerts?state=open`)
5. Each endpoint that returns 403/404 (insufficient permissions or feature not enabled) is
   treated as unavailable: set the count to `None` (not `0`) and emit a debug event. This
   distinguishes "no alerts" from "no access".
6. After the `TaskPool` exits, `_main` prints a summary report to stdout:
   ```
   Repos scanned:           42
   Repos with issues:       12
   Dependabot alerts:       34  (or "N/A" if all repos returned 403)
   Code scanning alerts:     8
   Secret scanning alerts:   3
   ```
7. For each repo with at least one open alert (any category), the report includes a
   per-repo section:
   ```
   owner/repo-name
     Dependabot alerts:       5
     Code scanning alerts:    2
     Secret scanning alerts:  0
   ```
   Repos where all three endpoints returned `None` (no access) are excluded from the
   per-repo section.
8. The report is printed to stdout; all logging continues to stderr. This keeps the report
   pipeable.
9. `SecurityRepoProcessor` follows the same error-resilience pattern as `InfoRepoProcessor`:
   per-step `GitHubApiError` → partial result; unexpected exception → failed; `FatalError`
   subclasses re-raised.

### Non-functional

- No new dependencies.
- `SecurityRepoProcessor` lives in `src/ghbot/processor.py` alongside `InfoRepoProcessor`.
- Report formatting lives in a new `src/ghbot/report.py` module.
- The `info` subcommand produces no report (existing behaviour: results collected in
  `pool.results` but not printed). This can be extended later.

---

## Constraints

- GitHub API via existing `github_api_call` context manager — no raw HTTP.
- All three security endpoints use `getiter` with `state=open` query param.
- `None` counts (no access) are displayed as `"N/A"` in the report; `0` means accessible
  but no open alerts.
- CLI uses Click's group/command pattern. Global options (`--owner`, `--config`,
  `--verbose`, `--quiet`, `--log-file`, `--log-level`, `--log-json`, `--requests`,
  `--concurrency`) move to the group; subcommands (`info`, `security`) are plain commands
  with no additional options for now.

---

## High-level Design

### CLI structure

```python
@click.group()
@click.option("--owner", ...)
@click.option("--config", ...)
# ... all existing global options ...
@click.pass_context
def cli(ctx, ...):
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = build_cfg(...)   # existing merge logic
    configure(...)                     # existing logging setup

@cli.command()
@click.pass_context
def info(ctx):
    asyncio.run(_main(ctx.obj["cfg"], processor_cls=InfoRepoProcessor))

@cli.command()
@click.pass_context
def security(ctx):
    asyncio.run(_main(ctx.obj["cfg"], processor_cls=SecurityRepoProcessor))
```

`_main` gains a `processor_cls` parameter. It constructs `LoggingMonitor` and
`processor_cls(owner, repo["name"], gh, monitor)` per repo, submits `processor.run` to the
pool, then calls `print_report(pool.results, processor_cls)` after the pool exits.

### SecurityRepoProcessor

```python
class SecurityRepoProcessor:
    def __init__(self, owner, repo, gh, monitor): ...

    async def run(self) -> RepoResult:
        # fetches dependabot_alerts, code_scanning_alerts, secret_scanning_alerts
        # each stored in result.results with int count or None
```

### Report

```python
# src/ghbot/report.py
def print_security_report(results: list[RepoResult]) -> None:
    # prints summary + per-repo breakdown to stdout
```

Called from `_main` only when `processor_cls is SecurityRepoProcessor`.

---

## Acceptance Criteria

- [ ] `ghbot` with no subcommand exits non-zero and prints usage
- [ ] `ghbot --owner x info` runs `InfoRepoProcessor` per repo
- [ ] `ghbot --owner x security` runs `SecurityRepoProcessor` per repo
- [ ] `SecurityRepoProcessor.run()` collects `dependabot_alerts`, `code_scanning_alerts`, `secret_scanning_alerts` (open only)
- [ ] 403/404 on any endpoint → count is `None`, debug event emitted, no error recorded
- [ ] `GitHubApiError` on any endpoint → count is `None`, error recorded, status `"partial"`
- [ ] `FatalError` subclasses re-raised from `run()`
- [ ] Summary report printed to stdout after pool exits (security subcommand only)
- [ ] Per-repo section printed only for repos with at least one non-None, non-zero count
- [ ] `None` counts displayed as `"N/A"` in report; `0` displayed as `0`
- [ ] All logging remains on stderr; report on stdout

---

## Contract

```json
{
  "output_files": [
    "src/ghbot/processor.py",
    "src/ghbot/report.py",
    "src/ghbot/__main__.py",
    "tests/unit/test_security_processor.py",
    "tests/unit/test_report.py",
    "tests/unit/test_main.py"
  ],
  "checks": [
    "ghbot with no subcommand exits non-zero",
    "info subcommand uses InfoRepoProcessor",
    "security subcommand uses SecurityRepoProcessor",
    "SecurityRepoProcessor collects dependabot_alerts, code_scanning_alerts, secret_scanning_alerts",
    "open alerts only (state=open query param)",
    "403/404 sets count to None, emits debug event, no error",
    "GitHubApiError sets count to None, records error, status partial",
    "FatalError subclasses re-raised",
    "summary report printed to stdout",
    "per-repo section only for repos with issues",
    "None displayed as N/A",
    "logging on stderr, report on stdout"
  ]
}
```
