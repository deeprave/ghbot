# ghbot

[![Validate](https://img.shields.io/github/actions/workflow/status/deeprave/ghbot/tests.yml?branch=main&label=validate&logo=github)](https://github.com/deeprave/ghbot/actions/workflows/tests.yml)
[![Security](https://img.shields.io/badge/security-CodeQL-blue.svg?logo=github)](https://github.com/deeprave/ghbot/security/code-scanning)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen.svg)](https://github.com/deeprave/ghbot)
[![PyPI version](https://img.shields.io/pypi/v/ghbot.svg?logo=pypi&logoColor=white)](https://pypi.org/project/ghbot/)
[![Python versions](https://img.shields.io/pypi/pyversions/ghbot.svg?logo=python&logoColor=white)](https://pypi.org/project/ghbot/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE.md)

An async command-line tool that scans GitHub repositories across one or more owners and reports on
them. `ghbot` is a small **engine** — repository discovery, bounded-concurrency execution, a GitHub
API layer, and report rendering — plus a set of **processors** that each answer one question about a
repository (security posture, open issues, …).

## Requirements

- By default, the [GitHub CLI](https://cli.github.com) (`gh`), installed and authenticated (`gh auth login`).
- Alternatively, an API token in `GITHUB_API_TOKEN` when using `--env` or `env = true`.

## Authentication

By default, `ghbot` has no credentials of its own. At startup it runs `gh auth token` and uses the
token that `gh` **already holds** from your `gh auth login` — it does **not** generate a new token.
Your effective access is therefore exactly your `gh` login's scopes.

Use the global `-e` / `--env` option, or set `env = true` in `ghbot.toml`, to read the API token
from `GITHUB_API_TOKEN` instead. `--no-env` overrides `env = true` for one invocation and returns
to the default `gh auth token` source. Environment-token mode never invokes `gh`; it fails clearly
if that variable is unset or empty. `GITHUB_TOKEN` is not used, so workflow tokens cannot change
local command behaviour accidentally.

The selected token is fetched once, cached in memory for the duration of the run, and never
written to disk. In the default mode, if `gh` is missing or you are not logged in, `ghbot` stops
with a clear message. `gh` is used **only** for the default token source — all repository data is
then fetched by calling the GitHub REST API **directly** (via `httpx` + `gidgethub`), not by
shelling out to `gh` for each request.

## Running

```bash
uvx ghbot --owner <owner> <command> [options]
```

`--owner` may be repeated or comma-separated, and targets a GitHub user or organisation. ghbot
scans repositories accessible to the configured token and skips archived repositories:

```bash
uvx ghbot --owner acme security
uvx ghbot --owner acme,globex issues --json --labels
```

(From a source checkout, use `uv run ghbot …` instead of `uvx ghbot …`.)

## Commands (built-in processors)

### `security` — open security findings

Scans each repository for open **Dependabot**, **code-scanning**, and **secret-scanning** alerts,
and open **Dependabot pull requests** (and how many are ready to merge once approvals are ignored).

```bash
uvx ghbot --owner acme security [--plain | --table | --json] [--output FILE]
```

| Option | Meaning |
|---|---|
| `--plain` (default) | Summary + a per-repo block for repos with findings |
| `--table` | Markdown table, one row per repo with findings |
| `--json` | Structured output for every scanned repo |
| `--output FILE` | Write the report to a file instead of stdout |

Counts that are unavailable (no access / feature off) show as `N/A` in text and `null` in JSON;
`0` means accessible with nothing open.

### `issues` — open issues and pull requests

Lists open **issues and pull requests** per repository, each tagged by `type` (`issue` or `pr`).
It also separately reports open Dependabot and other pull requests, with the number GitHub
considers merge-ready (`CLEAN`).

```bash
uvx ghbot --owner acme issues [--plain | --table | --json] [--labels] [--dates] [--output FILE]
```

| Option | Meaning |
|---|---|
| `--plain` (default) | Summary and per-repo PR metrics + `#<n> [<type>] <title>` lines |
| `--table` | One row per item, including Dependabot/other and merge-ready metric columns |
| `--json` | `repositories[]` with `open_item_count`, four PR count metrics, two oldest-creation timestamp metrics, JSON-only Dependabot PR detail, and an `items[]` array |
| `--labels` | Include GitHub labels (`+label` in plain, a `Labels` column in table, a `labels[]` array in JSON) |
| `--dates` | Include item creation date, time, and timezone abbreviation in plain/table output |
| `--output FILE` | Write the report to a file |

The summary splits `Open issues` and `Open PRs` and includes four PR metrics: Dependabot total and
merge-ready, plus other total and merge-ready. Plain/table omit repos with nothing open; JSON
includes every scanned repo. If the PR metrics cannot be fetched for any repository, the aggregate
is `N/A` in text or `null` in JSON; JSON also sets `pull_request_metrics_complete` to `false`.

JSON items always include `created_at`, `updated_at`, `url`, `author`, and `draft`, even without
`--dates`. Repository records also include oldest open Dependabot and other pull-request timestamps,
plus `dependabot_pull_requests`: detailed JSON records with number, URL, creation timestamp, draft
state, and merge readiness. `--dates` changes only human-readable output and converts GitHub's UTC
timestamps to the operator's local timezone.

### `drift` — commits since the latest stable release

Finds repositories whose configured default branch has commits newer than their latest published
stable GitHub release. Repositories without a stable release, or with no commits since it, are not
listed. For each reported repository, `drift` also indicates whether its GitHub Actions workflows
appear configured to publish to PyPI; this is configuration detection only and does not query PyPI.

```bash
uvx ghbot --owner acme drift [--plain | --table | --json] [--output FILE]
```

| Option | Meaning |
|---|---|
| `--plain` (default) | Summary + per-repository release, publication time, branch, commit count, and PyPI configuration |
| `--table` | Markdown table for repositories with commits since release |
| `--json` | Structured summary and reportable repositories; unknown PyPI configuration is `null` |
| `--output FILE` | Write the report to a file instead of stdout |

### `info` — repository summary statistics

Gathers per-repository facts (description, languages, contributors, latest release, file count, open
PRs/issues, security alerts). These are collected and logged during the scan; `info` does not
currently render a stdout report.

## Global options

Global options go **before** the command:

| Option | Meaning |
|---|---|
| `--owner <o>` | Owner(s) to scan; repeatable or comma-separated |
| `--concurrency <n>` | Max repositories processed at once (default 16) |
| `--config <path>` | Config file (see below) |
| `-e`, `--env` / `--no-env` | Read the API token from `GITHUB_API_TOKEN`, or override `env = true` to use `gh auth token` |
| `--verbose` / `--quiet` | Console log level: debug / warnings-only |
| `--log-file <path>` | Also write logs to a file |
| `--log-level <lvl>` | File log level: `trace`/`debug`/`info`/`warn`/`error` |
| `--log-json` | Structured JSON logs to the log file |
| `--requests` | Log HTTP request/response detail |

## Configuration

Options can be set in `ghbot.toml` (current directory) or `~/.config/ghbot/config.toml`. Some CLI flags override the file (notably `--owner`, `--concurrency`, `--log-file`, and `--log-json`); `--env` enables environment-token mode and `--no-env` disables it for one invocation.

```toml
owners = ["acme", "globex"]
concurrency = 16
log-level = "info"
log-json = false
env = true  # use GITHUB_API_TOKEN instead of gh auth token
```

## How it works

```
authentication source
      ├─ `--env`, or `env = true` without `--no-env` ─► GITHUB_API_TOKEN
      └─ `--no-env`, or otherwise ────────────────────► gh auth token
      │
scan_repositories(owners)          discover each accessible non-archived repo
      │  DiscoveredRepository(owner, metadata, owner_type) stream
TaskPool (bounded concurrency)     one processor instance per repo, run in parallel
      │
Processor.run() ─► RepoResult      fetch via the GitHub API, return structured results
      │
report renderer                    plain / table / JSON
```

- **GitHub API** access goes through a single wrapper that maps HTTP failures to typed errors
  (not-found, rate-limit, transient) so processors handle them uniformly.
- **Resilience**: a failed step yields a partial result rather than aborting the run; rate limits
  abort the pool cleanly.

## License

MIT — see [LICENSE.md](LICENSE.md).
