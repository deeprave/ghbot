# Spec Lite: Security Scanner

## Problem
Add a `security` subcommand that scans repos for open Dependabot, code scanning, and secret
scanning alerts, then prints a summary report to stdout. Introduce subcommand dispatch so
`info` and `security` are explicit — running `ghbot` without a subcommand is an error.

## CLI
```
ghbot --owner <name> info      # InfoRepoProcessor (existing)
ghbot --owner <name> security  # SecurityRepoProcessor (new)
ghbot --owner <name>           # error: must specify a subcommand
```

Global options (`--owner`, `--config`, `--verbose`, `--quiet`, `--log-file`, `--log-level`,
`--log-json`, `--requests`, `--concurrency`) move to the Click group. Subcommands have no
additional options.

## Key Requirements
1. `SecurityRepoProcessor` in `processor.py` collects three data points (open alerts only):
   - `dependabot_alerts` — `GET /repos/{owner}/{repo}/dependabot/alerts?state=open`
   - `code_scanning_alerts` — `GET /repos/{owner}/{repo}/code-scanning/alerts?state=open`
   - `secret_scanning_alerts` — `GET /repos/{owner}/{repo}/secret-scanning/alerts?state=open`
2. 403/404 on any endpoint → count is `None` (not `0`), debug event, no error recorded
3. `GitHubApiError` → count is `None`, error recorded, status `"partial"`
4. `FatalError` subclasses re-raised (same pattern as `InfoRepoProcessor`)
5. After pool exits, `security` subcommand prints report to stdout via `print_security_report()`
6. `info` subcommand produces no report

## Report Format
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
- Per-repo section only for repos with at least one non-None, non-zero count
- `None` → `"N/A"`; `0` → `0`
- Report to stdout; logging to stderr

## New Files
- `src/ghbot/report.py` — `print_security_report(results: list[RepoResult]) -> None`
- `tests/unit/test_security_processor.py`
- `tests/unit/test_report.py`

## Modified Files
- `src/ghbot/processor.py` — add `SecurityRepoProcessor`
- `src/ghbot/__main__.py` — refactor to Click group + `info`/`security` subcommands;
  `_main` gains `processor_cls` parameter
- `tests/unit/test_main.py` — update for new CLI structure
