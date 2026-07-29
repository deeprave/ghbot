# Implementation Plan: scan-issues

## Overview

Add the `issues` subcommand and `IssuesRepoProcessor` in TDD slices, then the report rendering with
`--labels` gating. Keep the change focused on `processor.py`, `report.py`, `__main__.py`, and tests.

## Tasks

- [ ] 1. Add processor tests for open-issue collection
  - [ ] 1.1 Add tests that open issues are counted under `open_issue_count`.
  - [ ] 1.2 Add tests that items carrying a `pull_request` field are excluded from count and list.
  - [ ] 1.3 Add tests that `open_issues` records carry `number`, `title`, and `labels`, preserving
    GitHub's returned order.
  - [ ] 1.4 Add tests that the endpoint uses `state=open` (closed issues not requested).
  - [ ] 1.5 Add tests that issues endpoint 403/404 sets `open_issue_count` and `open_issues` to
    `None` without recording an error.
  - [ ] 1.6 Add tests that issues endpoint `GitHubApiError` records an error and sets result status
    to `"partial"`.
  - [ ] 1.7 Add a test that fatal rate-limit errors are re-raised.

- [ ] 2. Implement `IssuesRepoProcessor`
  - [ ] 2.1 Add `IssuesRepoProcessor` to `processor.py` with the standard constructor signature.
  - [ ] 2.2 Add `_fetch_open_issues()` using `github_api_call` and
    `getiter("/repos/{owner}/{repo}/issues?state=open", ...)`.
  - [ ] 2.3 Exclude pull requests and build compact `{number, title, labels}` records.
  - [ ] 2.4 Store `open_issue_count` and `open_issues`; set both to `None` on unavailability.
  - [ ] 2.5 Preserve fatal/non-fatal error behavior and the deferred progress/activity-message
    pattern.

- [ ] 3. Add report tests for issue rendering
  - [ ] 3.1 Add plain summary expectations (repos scanned, repos with open issues, open issues).
  - [ ] 3.2 Add plain per-repo expectations for `#<number> <description>` lines.
  - [ ] 3.3 Add plain expectations that `--labels` appends `+label` suffixes and default omits them.
  - [ ] 3.4 Add table expectations for one row per issue (`Repository | # | Description`).
  - [ ] 3.5 Add table expectations that the `Labels` column appears only with `--labels` and renders
    a comma-separated list.
  - [ ] 3.6 Add table expectations for long-description truncation.
  - [ ] 3.7 Add JSON expectations for summary and repository/issue keys, `labels` gated by
    `--labels`, `None` count preserved as `null`, and all scanned repos included.
  - [ ] 3.8 Add expectations that plain and table omit repositories with no open issues.

- [ ] 4. Implement report rendering
  - [ ] 4.1 Add `render_issues_report` / `print_issues_report` to `report.py`.
  - [ ] 4.2 Add the summary block with `None`-aware open-issue total.
  - [ ] 4.3 Add plain per-repo rendering with optional `+label` suffixes.
  - [ ] 4.4 Add table rendering with the optional `Labels` column and description truncation.
  - [ ] 4.5 Add JSON rendering with the optional per-issue `labels` field.

- [ ] 5. Wire the `issues` subcommand
  - [ ] 5.1 Add CLI tests that `issues` dispatches `IssuesRepoProcessor`.
  - [ ] 5.2 Add CLI tests for mutually-exclusive `--plain/--table/--json` and for `--output`.
  - [ ] 5.3 Add the `issues` command to the Click group reusing `_output_format`, with `--labels`
    and `--output`, calling `print_issues_report` after `_main`.

- [ ] 6. Final verification
  - [ ] 6.1 Update `spec-lite.md` with the implemented behavior summary.
  - [ ] 6.2 Run `uv run pytest -v -Werror -Walways`.
  - [ ] 6.3 Run `uv run ruff check`.
  - [ ] 6.4 Run `uv run ty check src/`.
  - [ ] 6.5 Run `uv run ruff format --check`.
