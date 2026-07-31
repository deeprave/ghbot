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
repository (security posture, open issues, …). New capabilities are added by writing a processor.

## Requirements

- The [GitHub CLI](https://cli.github.com) (`gh`), installed and authenticated (`gh auth login`).

## Authentication

`ghbot` has no credentials of its own. At startup it runs `gh auth token` and uses the token that
`gh` **already holds** from your `gh auth login` — it does **not** generate a new token. Your
effective access is therefore exactly your `gh` login's scopes.

That token is fetched once, cached in memory for the duration of the run, and never written to disk
(if `gh` is missing or you're not logged in, `ghbot` stops with a clear message). `gh` is used
**only** to obtain the token — all repository data is then fetched by calling the GitHub REST API
**directly** (via `httpx` + `gidgethub`), not by shelling out to `gh` for each request.

## Running

```bash
uvx ghbot --owner <owner> <command> [options]
```

`--owner` may be repeated or comma-separated, and targets a GitHub user (all of that user's
repositories are scanned):

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

```bash
uvx ghbot --owner acme issues [--plain | --table | --json] [--labels] [--output FILE]
```

| Option | Meaning |
|---|---|
| `--plain` (default) | Per-repo header + `#<n> [<type>] <title>` lines |
| `--table` | One row per item: `Repository │ # │ Type │ Description` |
| `--json` | `repositories[]` with `open_item_count` and an `items[]` array |
| `--labels` | Include GitHub labels (`+label` in plain, a `Labels` column in table, a `labels[]` array in JSON) |
| `--output FILE` | Write the report to a file |

The summary splits `Open issues` and `Open PRs`. Plain/table omit repos with nothing open; JSON
includes every scanned repo.

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
| `--verbose` / `--quiet` | Console log level: debug / warnings-only |
| `--log-file <path>` | Also write logs to a file |
| `--log-level <lvl>` | File log level: `trace`/`debug`/`info`/`warn`/`error` |
| `--log-json` | Structured JSON logs to the log file |
| `--requests` | Log HTTP request/response detail |

## Configuration

Options can be set in `ghbot.toml` (current directory) or `~/.config/ghbot/config.toml`. Some CLI flags override the file (notably `--owner`, `--concurrency`, `--log-file`, and `--log-json`).

```toml
owners = ["acme", "globex"]
concurrency = 16
log-level = "info"
log-json = false
```

## How it works

```
gh auth token
      │
scan_repositories(owners)          discover every repo for each owner
      │  (owner, repo) stream
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
- The **extension point is the processor** — everything else is stable engine.

## Extending ghbot: adding a processor

A processor is any object implementing the `RepoProcessor` protocol (`src/ghbot/processor.py`):

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class RepoProcessor(Protocol):
    @property
    def owner(self) -> str: ...
    @property
    def repo(self) -> str: ...
    async def run(self) -> RepoResult: ...
```

It returns a `RepoResult`:

```python
@dataclass(slots=True)
class RepoResult:
    owner: str
    repo: str
    status: ProcessingStatus = "success"  # "success" | "partial" | "failed"
    errors: list[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)  # your data goes here
```

### 1. Write the processor

Constructors take `(owner, repo, gh, monitor, options=None)`. Fetch through `github_api_call` and
build URLs with `url_vars` (never f-strings). Follow the standard per-step error policy: treat
403/404 as "unavailable" (store `None`, don't error), turn a non-fatal `GitHubApiError` into a
partial result, and re-raise rate-limit errors so the pool can handle them.

```python
from ghbot.processor import RepoResult, FeedbackEvent
from ghbot.github.client import github_api_call
from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)


class TagsRepoProcessor:
    """Counts a repository's tags."""

    def __init__(self, owner, repo, gh, monitor, options=None):
        if not owner or not repo:
            raise ValueError("owner and repo are required")
        self._owner, self._repo, self._gh, self._monitor = owner, repo, gh, monitor

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

    async def run(self) -> RepoResult:
        result = RepoResult(owner=self._owner, repo=self._repo)
        try:
            async with github_api_call(self._gh):
                tags = [
                    t
                    async for t in self._gh.getiter(
                        "/repos/{owner}/{repo}/tags",
                        url_vars={"owner": self._owner, "repo": self._repo},
                    )
                ]
            result.results["tag_count"] = len(tags)
        except GitHubNotFoundError:
            result.results["tag_count"] = None
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as e:
            result.results["tag_count"] = None
            result.errors.append(f"tags: {e}")
            result.status = "partial"
        return result
```

Use the injected `monitor` (`await self._monitor.send_event(FeedbackEvent(type, severity, message))`)
for progress/feedback. `InfoRepoProcessor` and `SecurityRepoProcessor` are worked examples.

### 2. Wire a subcommand

Add a Click command in `src/ghbot/__main__.py` that runs your processor across all discovered repos
via the shared engine, then (optionally) renders a report:

```python
@cli.command()
@click.pass_context
def tags(ctx):
    """Count repository tags."""
    cfg = ctx.obj["cfg"]
    results = asyncio.run(_main(cfg, TagsRepoProcessor))
    # render results as you like, e.g. a function in report.py
```

`_main(cfg, processor_cls)` handles auth, discovery, concurrency, and per-repo construction — you
only supply the processor (and, if it needs one, a renderer in `src/ghbot/report.py`).

### 3. Test it

Mirror `tests/unit/test_*_processor.py`: patch `ghbot.processor.github_api_call`, drive `run()` with
a mocked `gh`, and assert on `result.results` / `result.status` / `result.errors`.

## Development

```bash
uv sync
uv run pytest -q          # tests
uv run ruff check         # lint
uv run ruff format        # format
uv run ty check src/      # type check
```

Contributions go through pull requests; `main` is protected and gated by the `Validate` workflow.

## License

MIT — see [LICENSE.md](LICENSE.md).
 