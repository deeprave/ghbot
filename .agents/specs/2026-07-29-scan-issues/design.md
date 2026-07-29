# Design Document: scan-issues

## Overview

Add an `issues` subcommand backed by a new `IssuesRepoProcessor` that collects, per repository:

```text
open_issue_count   # int | None
open_issues        # list[IssueRecord] | None
```

Each `IssueRecord` carries `number`, `title`, and `labels` (list of label names). The processor
lists open issues, drops pull requests, and stores compact records. A new report renderer in
`report.py` produces plain, table, and JSON output; a `--labels` flag governs whether label data is
rendered in any format.

This mirrors the existing `SecurityRepoProcessor` + `report.py` architecture: scan per repo via the
`TaskPool`, then render `pool.results` after the pool exits.

## Architecture

```text
cli group
  └─ issues subcommand
       ├─ _output_format(plain, table, json)         # reuse existing helper
       ├─ asyncio.run(_main(cfg, IssuesRepoProcessor))
       └─ print_issues_report(results, format=..., labels=..., output=...)

IssuesRepoProcessor.run()
  └─ _fetch_open_issues()
       ├─ getiter /repos/{owner}/{repo}/issues?state=open
       ├─ drop items with a "pull_request" field
       └─ store open_issue_count + open_issues (number, title, labels)

report module
  ├─ summary totals: repos scanned, repos with issues, open issues
  ├─ plain: per-repo header + "#<n> <title>" lines (+labels when enabled)
  ├─ table: one row per issue (Repository | # | Description [| Labels])
  └─ JSON: summary + repositories[] each with issues[] (labels field when enabled)
```

## GitHub API

Use existing `github_api_call(self._gh)` for the request.

### List Open Issues

```text
GET /repos/{owner}/{repo}/issues?state=open
```

Use `getiter` and `url_vars={"owner": self._owner, "repo": self._repo}`.

Pull-request exclusion (GitHub returns PRs through the issues endpoint):

```python
def _is_pull_request(item: dict) -> bool:
    return "pull_request" in item
```

Label extraction (labels ship inside each issue payload — no extra request):

```python
def _issue_labels(item: dict) -> list[str]:
    return [
        label["name"]
        for label in (item.get("labels") or [])
        if isinstance(label, dict) and label.get("name")
    ]
```

## Result Records

Store a compact record per issue rather than the raw payload:

```python
result.results["open_issue_count"] = count_or_none
result.results["open_issues"] = [
    {"number": item["number"], "title": item.get("title") or "", "labels": _issue_labels(item)}
    for item in kept_issues
]
```

Labels are always captured; the `--labels` flag only affects rendering. When the endpoint is
unavailable or errors, both `open_issue_count` and `open_issues` are `None`.

## Processor Skeleton

```python
class IssuesRepoProcessor:
    def __init__(self, owner, repo, gh, monitor, options=None): ...

    async def run(self) -> RepoResult:
        result = RepoResult(owner=self._owner, repo=self._repo)
        try:
            await self._fetch_open_issues(result)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except FatalError:
            raise
        except Exception as e:
            ...  # status = "failed", record error
        else:
            if result.errors:
                result.status = "partial"
        return result
```

Progress/monitor behavior follows the security processor's deferred-event pattern: buffer debug
progress events, and emit a concise activity message (e.g. `found 3 open issues`) only for
repositories that actually have open issues, so clean repositories stay quiet.

## Error Handling

Follow the current processor policy:

| Condition | Handling |
|---|---|
| Issues endpoint 403/404 | set `open_issue_count` and `open_issues` to `None`, emit deferred debug event, no error |
| Issues endpoint `GitHubApiError` | set both to `None`, emit error event, append error, status partial |
| Fatal rate-limit errors | re-raise |
| Unexpected exception | existing `run()` containment sets result failed |

## Report Rendering

New entry point in `report.py`:

```python
def print_issues_report(results, *, format="plain", labels=False, output=None) -> None: ...
def render_issues_report(results, *, format="plain", labels=False) -> str: ...
```

### Summary block (all formats' text; mirrored in JSON)

```text
Repos scanned:            42
Repos with open issues:   12
Open issues:             137
```

`Open issues` is `None`-aware (sum of non-`None` counts; `"N/A"` when all `None`), reusing the same
`_total` / `_display` helpers already in `report.py`.

### Plain

```text
owner/repo-a  (2 open)
  #12 Fix the login redirect
  #15 Docs typo in README

owner/repo-b  (1 open)
  #3 Flaky test on CI
```

With `--labels`, each line gains `+`-prefixed labels:

```text
  #12 Fix the login redirect +bug +urgent
```

Only repositories with at least one open issue appear.

### Table

One row per issue, summary block above it:

```text
|Repository        |    #|Description             |
|------------------|-----|------------------------|
|owner/repo-a      |   12|Fix the login redirect  |
|owner/repo-a      |   15|Docs typo in README     |
|owner/repo-b      |    3|Flaky test on CI        |
```

With `--labels`, a trailing `Labels` column is added rendering a comma-separated list:

```text
|Repository        |    #|Description             |Labels        |
|------------------|-----|------------------------|--------------|
|owner/repo-a      |   12|Fix the login redirect  |bug, urgent   |
```

Fixed column widths follow the existing table constants style in `report.py`. Descriptions longer
than the `Description` column are truncated with a trailing `…`; plain and JSON keep the full title.
Only repositories with open issues contribute rows.

### JSON

```json
{
  "summary": {
    "repos_scanned": 42,
    "repos_with_issues": 12,
    "open_issues": 137
  },
  "repositories": [
    {
      "owner": "owner",
      "repo": "repo-a",
      "repository": "owner/repo-a",
      "open_issue_count": 2,
      "issues": [
        {"number": 12, "title": "Fix the login redirect", "labels": ["bug", "urgent"]},
        {"number": 15, "title": "Docs typo in README", "labels": ["docs"]}
      ]
    }
  ]
}
```

The `labels` field on each issue object is present only when `--labels` is passed. `open_issue_count`
is preserved as `null` when unavailable. Every scanned repository is included.

## CLI Wiring

```python
@cli.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option("--labels", "show_labels", is_flag=True, default=False)
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.pass_context
def issues(ctx, format_plain, format_table, format_json, show_labels, output):
    """Scan repositories for open issues."""
    cfg = ctx.obj["cfg"]
    output_format = _output_format(plain=format_plain, table=format_table, json_format=format_json)
    try:
        results = asyncio.run(_main(cfg, IssuesRepoProcessor))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)
    print_issues_report(results, format=output_format, labels=show_labels, output=output)
```

`_main` is unchanged; the processor takes the same constructor signature as the others.

## Test Strategy

- Processor tests: open issues counted; pull requests excluded from count and list; labels captured;
  GitHub ordering preserved.
- Processor tests: issues endpoint 403/404 → both result keys `None`, no error; `GitHubApiError` →
  both `None`, error recorded, status `"partial"`; fatal rate limits re-raised.
- Report tests: plain summary + per-repo lines; `#<n> <title>` formatting; `--labels` adds
  `+label` suffixes; no-label default omits suffixes.
- Report tests: table rows per issue; `Labels` column present only with `--labels`; description
  truncation; repositories without issues omitted.
- Report tests: JSON summary + repositories; `labels` field gated by `--labels`; `None` count
  preserved as `null`; all scanned repos included.
- CLI tests: `issues` subcommand dispatches `IssuesRepoProcessor`; mutually-exclusive format flags;
  `--output` writes to file.
- Full verification:
  - `uv run pytest -v -Werror -Walways`
  - `uv run ruff check`
  - `uv run ty check src/`
  - `uv run ruff format --check`
