# Spec Lite: Scan Issues

## Problem

ghbot can scan repositories for metadata (`info`) and security findings (`security`), but has no
command for open issue tracking across an owner's repositories.

## Goal

Add an `issues` subcommand backed by a new `IssuesRepoProcessor` that reports, per repository:

- `open_issue_count` — number of open issues (pull requests excluded)
- `open_issues` — ordered list of `{number, title, labels}` records

## CLI

```
ghbot --owner <name> issues [--plain|--table|--json] [--labels] [--output FILE]
```

Format flags are mutually exclusive, default `--plain`, reusing the `security` selection helper.
`--labels` (default off) enables label rendering.

## Output

- **plain**: per-repo header + one `#<number> <description>` line per issue. With `--labels`, each
  line gains `+`-prefixed labels: `#12 Fix the login redirect +bug +urgent`.
- **table**: one row per issue — `Repository | # | Description`; with `--labels`, a trailing
  `Labels` column rendered as a comma-separated list.
- **json**: summary + `repositories[]`, each with `open_issue_count` and an `issues[]` array of
  `{number, title}`; with `--labels`, each issue object also carries a `labels` array.

Pull requests are excluded everywhere. Plain and table omit repositories with no open issues; JSON
includes every scanned repository. A `None` count displays as `N/A` in text and `null` in JSON.

## Design

- List issues with `GET /repos/{owner}/{repo}/issues?state=open` via `getiter`.
- Drop items carrying a `pull_request` field.
- Extract labels from each issue's `labels` array (no extra request); always captured, rendered
  only when `--labels` is set.
- Store `open_issue_count` and `open_issues` in `RepoResult.results`.
- Preserve the existing processor error policy and the security processor's deferred progress/
  activity-message pattern.

## Verification

- `uv run pytest -v -Werror -Walways`
- `uv run ruff check`
- `uv run ty check src/`
- `uv run ruff format --check`

## Implementation Status

Not started. Requirements and design defined.
