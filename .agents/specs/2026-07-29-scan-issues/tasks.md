# Implementation Plan: scan-issues (revised — include pull requests)

## Overview

Revise the implemented `issues` feature to include pull requests alongside issues, tag each item by
`type` (`"issue"`/`"pr"`), rename the result keys to `open_item_count` / `open_items`, split the
summary into `Open issues` / `Open PRs`, and render the type in every format. TDD throughout,
modifying the existing `processor.py`, `report.py`, `__main__.py`, and their tests.

## Tasks

- [x] 1. Revise processor tests for open-item collection
  - [x] 1.1 Rename result-key assertions to `open_item_count` / `open_items`.
  - [x] 1.2 Replace the PR-exclusion tests: pull requests are now included and counted.
  - [x] 1.3 Add tests that each record carries `type` (`"pr"` when the item has a `pull_request`
    field, else `"issue"`), preserving GitHub's order across mixed issues/PRs.
  - [x] 1.4 Keep tests for `state=open`, records carrying `number`/`title`/`labels`, 403/404 → both
    keys `None` no error, `GitHubApiError` → both `None` + partial, and fatal re-raise (renamed).

- [x] 2. Revise `IssuesRepoProcessor`
  - [x] 2.1 Rename `_fetch_open_issues` → `_fetch_open_items`; stop excluding pull requests.
  - [x] 2.2 Add `_item_type()`; build `{number, title, type, labels}` records.
  - [x] 2.3 Store `open_item_count` / `open_items`; keep `None`-on-unavailability and error policy.
  - [x] 2.4 Rename the activity message to items (e.g. `found N open items`).

- [x] 3. Revise report tests for item rendering
  - [x] 3.1 Update summary tests: `Repos with open items`, split `Open issues` / `Open PRs`
    (`None`-aware totals).
  - [x] 3.2 Update plain tests: lines are `#<number> [<type>] <description>`; `--labels` appends
    `+label`.
  - [x] 3.3 Update table tests: add the `Type` column; `Labels` column still only with `--labels`;
    truncation preserved.
  - [x] 3.4 Update JSON tests: `items[]` with `number`/`title`/`type`; `type` always present;
    `labels` gated; `open_item_count` null preserved; split summary keys; all repos included.
  - [x] 3.5 Keep tests that plain/table omit repositories with no open items.

- [x] 4. Revise report rendering
  - [x] 4.1 Rename helpers/keys to items; count "open items" via `open_item_count`.
  - [x] 4.2 Add per-type totals and the split `Open issues` / `Open PRs` summary lines.
  - [x] 4.3 Plain: render `#<number> [<type>] <description>` (+ optional labels).
  - [x] 4.4 Table: add the `Type` column (keep optional `Labels` column and truncation).
  - [x] 4.5 JSON: emit `type` on every item; keep `labels` gated by `--labels`.

- [x] 5. Verify CLI wiring
  - [x] 5.1 Update the `issues` command docstring/help to mention pull requests.
  - [x] 5.2 Confirm CLI tests still pass (names `IssuesRepoProcessor` / `print_issues_report`
    unchanged); adjust any assertions that referenced the old keys.

- [x] 6. Final verification
  - [x] 6.1 Update `spec-lite.md` with the implemented behavior summary.
  - [x] 6.2 Run `uv run pytest -v -Werror -Walways`.
  - [x] 6.3 Run `uv run ruff check`.
  - [x] 6.4 Run `uv run ty check src/`.
  - [x] 6.5 Run `uv run ruff format --check`.
