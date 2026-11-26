# Spec Lite: Scan Issues

## Problem

ghbot has no command for open work-item tracking across an owner's repositories, covering both
issues and pull requests.

## Goal

Add an `issues` subcommand backed by a new `IssuesRepoProcessor` that reports, per repository:

- `open_item_count` — number of open items (issues + pull requests)
- `open_items` — ordered list of `{number, title, type, labels}` records, where `type` is `"issue"`
  or `"pr"`

Pull requests are **included** (GitHub's issues endpoint returns them) and tagged by type.

## CLI

```
ghbot --owner <name> issues [--plain|--table|--json] [--labels] [--output FILE]
```

Format flags are mutually exclusive, default `--plain`. `--labels` (default off) enables GitHub-label
rendering. The `type` tag is always shown.

## Output

- **plain**: per-repo header + one `#<number> [<type>] <description>` line per item. With `--labels`,
  each line gains `+`-prefixed labels: `#12 [pr] Fix the login redirect +bug +urgent`.
- **table**: one row per item — `Repository | # | Type | Description`; with `--labels`, a trailing
  comma-separated `Labels` column.
- **json**: summary + `repositories[]`, each with `open_item_count` and an `items[]` array of
  `{number, title, type}`; with `--labels`, each item also carries a `labels` array.

Summary splits counts: `Repos scanned`, `Repos with open items`, `Open issues`, `Open PRs`.
Plain/table omit repos with no open items; JSON includes every scanned repo. A `None` count shows as
`N/A` in text and `null` in JSON.

## Design

- List items with `GET /repos/{owner}/{repo}/issues?state=open` via `getiter` (returns issues and
  PRs; PRs carry a `pull_request` field).
- Tag `type = "pr" if "pull_request" in item else "issue"` — no exclusion.
- Extract GitHub labels from each item's `labels` array (always captured; rendered only with
  `--labels`).
- Store `open_item_count` and `open_items` in `RepoResult.results`.
- Preserve the existing processor error policy and the security processor's deferred progress /
  activity-message pattern.

## Verification

- `uv run pytest -v -Werror -Walways`
- `uv run ruff check`
- `uv run ty check src/`
- `uv run ruff format --check`

## Implementation Status

Complete. `IssuesRepoProcessor` collects `open_item_count` and `open_items`
(`{number, title, type, labels}`, issues + pull requests, tagged by `type`) via
`GET /repos/{owner}/{repo}/issues?state=open`, following the existing error policy and the security
processor's deferred progress/activity pattern. `report.py` renders plain (`#<n> [<type>] <title>`),
table (with a `Type` column), and JSON (`type` on every item), with the split `Open issues` /
`Open PRs` summary and GitHub labels gated behind `--labels`; long descriptions truncate with `…` in
table only. The `issues` subcommand is wired in `__main__.py`. Verified: 266 tests pass; `ruff
check`, `ty check src/`, and `ruff format --check` all clean.
