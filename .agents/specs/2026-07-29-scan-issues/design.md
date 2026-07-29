# Design Document: scan-issues

## Overview

Add an `issues` subcommand backed by a new `IssuesRepoProcessor` that collects, per repository:

```text
open_item_count   # int | None  (issues + pull requests)
open_items        # list[ItemRecord] | None
```

Each `ItemRecord` carries `number`, `title`, `type` (`"issue"` or `"pr"`), and `labels` (list of
label names). The processor lists open items (GitHub returns pull requests alongside issues), tags
each by type, and stores compact records. A new report renderer in `report.py` produces plain,
table, and JSON output; a `--labels` flag governs whether GitHub-label data is rendered. The type
tag is always shown.

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
  └─ _fetch_open_items()
       ├─ getiter /repos/{owner}/{repo}/issues?state=open
       ├─ tag each item type = "pr" if "pull_request" in item else "issue"
       └─ store open_item_count + open_items (number, title, type, labels)

report module
  ├─ summary totals: repos scanned, repos with open items, open issues, open PRs
  ├─ plain: per-repo header + "#<n> [<type>] <title>" lines (+labels when enabled)
  ├─ table: one row per item (Repository | # | Type | Description [| Labels])
  └─ JSON: summary + repositories[] each with items[] (labels field when enabled)
```

## GitHub API

Use existing `github_api_call(self._gh)` for the request.

### List Open Items

```text
GET /repos/{owner}/{repo}/issues?state=open
```

Use `getiter` and `url_vars={"owner": self._owner, "repo": self._repo}`. This endpoint returns both
issues and pull requests; pull requests carry a `pull_request` field.

Type classification (no exclusion — every item is kept):

```python
def _item_type(item: dict) -> str:
    return "pr" if "pull_request" in item else "issue"
```

Label extraction (labels ship inside each item payload — no extra request):

```python
def _item_labels(item: dict) -> list[str]:
    return [
        label["name"]
        for label in (item.get("labels") or [])
        if isinstance(label, dict) and label.get("name")
    ]
```

## Result Records

```python
result.results["open_item_count"] = count_or_none
result.results["open_items"] = [
    {
        "number": item["number"],
        "title": item.get("title") or "",
        "type": _item_type(item),
        "labels": _item_labels(item),
    }
    for item in items
]
```

`type` and `labels` are always captured; the `--labels` flag only affects label rendering. When the
endpoint is unavailable or errors, both `open_item_count` and `open_items` are `None`.

## Processor Skeleton

Same shape as `SecurityRepoProcessor`: standard constructor (validates owner/repo), a `run()` that
calls `_fetch_open_items()` with the existing error containment, and the deferred progress /
activity-message pattern — buffer debug events, emit a concise activity message (e.g.
`found 3 open items`) only for repositories that actually have open items.

## Error Handling

| Condition | Handling |
|---|---|
| Endpoint 403/404 | set `open_item_count` and `open_items` to `None`, emit deferred debug event, no error |
| Endpoint `GitHubApiError` | set both to `None`, emit error event, append error, status partial |
| Fatal rate-limit errors | re-raise |
| Unexpected exception | existing `run()` containment sets result failed |

## Report Rendering

Entry points in `report.py` (unchanged names): `render_issues_report` / `print_issues_report` with
`format` and `labels` params.

### Summary block

```text
Repos scanned:            42
Repos with open items:    12
Open issues:             120
Open PRs:                 17
```

`Open issues` / `Open PRs` are per-type totals across repositories, `None`-aware (a repository whose
`open_items` is `None` contributes nothing; `"N/A"` when every repository is `None`). Reuse
`_display_total`; add a per-type total helper that counts records by `type` from `open_items`.

### Plain

```text
acme/api  (1 open)
  #3 [pr] Bump urllib3 to 2.2.1 +dependencies

acme/web  (2 open)
  #12 [issue] Fix the login redirect
  #15 [pr] Add retry to fetch
```

Line format: `#<number> [<type>] <title>`, with `+`-prefixed labels appended when `--labels`. Only
repositories with at least one open item appear.

### Table

One row per item, summary block above it:

```text
|Repository        |    #|Type |Description             |
|------------------|-----|-----|------------------------|
|acme/web          |   12|issue|Fix the login redirect  |
|acme/web          |   15|pr   |Add retry to fetch      |
```

With `--labels`, a trailing `Labels` column is added (comma-separated list). Descriptions longer
than the `Description` column are truncated with a trailing `…`; plain and JSON keep the full title.
Only repositories with open items contribute rows.

### JSON

```json
{
  "summary": {
    "repos_scanned": 42,
    "repos_with_items": 12,
    "open_issues": 120,
    "open_prs": 17
  },
  "repositories": [
    {
      "owner": "acme",
      "repo": "web",
      "repository": "acme/web",
      "open_item_count": 2,
      "items": [
        {"number": 12, "title": "Fix the login redirect", "type": "issue"},
        {"number": 15, "title": "Add retry to fetch", "type": "pr"}
      ]
    }
  ]
}
```

The `labels` field on each item object is present only when `--labels` is passed. `type` is always
present. `open_item_count` is preserved as `null` when unavailable. Every scanned repository is
included.

## CLI Wiring

Unchanged from the current implementation: the `issues` command reuses `_output_format`, has
`--labels` and `--output`, and calls `print_issues_report(results, format=..., labels=...,
output=...)` after `_main(cfg, IssuesRepoProcessor)`. Only the command docstring/help updates to
mention pull requests.

## Test Strategy

- Processor tests: issues and pull requests both counted; each record tagged `type` correctly;
  labels captured; order preserved across mixed issues/PRs.
- Processor tests: endpoint 403/404 → both keys `None`, no error; `GitHubApiError` → both `None`,
  error, status `"partial"`; fatal rate limits re-raised.
- Report tests: plain per-repo lines `#<n> [<type>] <title>`; `--labels` adds `+label` suffixes.
- Report tests: table rows per item with a `Type` column; `Labels` column only with `--labels`;
  description truncation; repositories without items omitted.
- Report tests: split summary (`Open issues` / `Open PRs`) with `None`-aware totals; JSON summary +
  repository/item keys; `type` always present; `labels` gated; `open_item_count` null preserved;
  all scanned repos in JSON.
- CLI tests: `issues` dispatches `IssuesRepoProcessor`; mutually-exclusive flags; `--labels`;
  `--output`.
- Full verification: `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check
  src/`, `uv run ruff format --check`.
