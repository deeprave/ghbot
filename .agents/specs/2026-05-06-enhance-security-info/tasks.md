# Implementation Plan: enhance-security-info

## Overview

Add Dependabot pull request remediation counts to the existing security scanner in TDD slices.
Keep the change focused on `SecurityRepoProcessor`, report rendering, and tests.

## Tasks

- [x] 1. Add processor tests for Dependabot pull request discovery
  - [x] 1.1 Add tests that open PRs authored by `dependabot[bot]` are counted.
  - [x] 1.2 Add tests that non-Dependabot PRs are ignored.
  - [x] 1.3 Add tests that closed PRs are not requested because the endpoint uses `state=open`.
  - [x] 1.4 Add tests that PR endpoint 403/404 sets `dependabot_open_pull_requests` and
    `dependabot_ready_pull_requests` to `None` without recording an error.
  - [x] 1.5 Add tests that PR endpoint `GitHubApiError` records an error and sets result status
    to `"partial"`.

- [x] 2. Implement open Dependabot PR counting
  - [x] 2.1 Add `_fetch_dependabot_pull_requests()` to `SecurityRepoProcessor`.
  - [x] 2.2 Call it from `SecurityRepoProcessor.run()` after the existing alert fetches.
  - [x] 2.3 Use `github_api_call` and `getiter("/repos/{owner}/{repo}/pulls?state=open", ...)`.
  - [x] 2.4 Filter to Dependabot-authored PRs and store `dependabot_open_pull_requests`.
  - [x] 2.5 Preserve existing fatal and non-fatal error behavior.

- [x] 3. Add processor tests for ready Dependabot PR counting
  - [x] 3.1 Add tests where successful commit status and successful check runs count a PR as ready.
  - [x] 3.2 Add tests where failing, error, or pending commit status prevents readiness.
  - [x] 3.3 Add tests where queued, in-progress, failing, cancelled, timed-out, or action-required
    check runs prevent readiness.
  - [x] 3.4 Add tests where `success`, `neutral`, and `skipped` completed check runs are
    non-blocking.
  - [x] 3.5 Add tests that draft PRs do not count as ready.
  - [x] 3.6 Add tests that `mergeable is False` does not count as ready.
  - [x] 3.7 Add tests that review approval state does not affect readiness.
  - [x] 3.8 Add tests that no reported statuses and no check runs count as ready when the PR is
    otherwise mergeable and not draft.

- [x] 4. Implement ready Dependabot PR counting
  - [x] 4.1 Add helpers for commit status readiness and check-run readiness.
  - [x] 4.2 Use the PR head SHA for status and check-run lookups.
  - [x] 4.3 Store `dependabot_ready_pull_requests`.
  - [x] 4.4 Treat approval/review fields as out of scope.
  - [x] 4.5 Treat per-PR status/check inspection `GitHubApiError` as partial and exclude that PR
    from the ready count.

- [x] 5. Update report tests
  - [x] 5.1 Add plain summary and per-repository expectations for `Dependabot PRs` and
    `Dependabot PRs ready`.
  - [x] 5.2 Add table expectations for open and ready Dependabot PR columns.
  - [x] 5.3 Add JSON expectations for summary and repository keys.
  - [x] 5.4 Add tests that non-zero Dependabot PR counts include a repository in text reports.
  - [x] 5.5 Add tests that all-zero or all-`None` alert and PR counts omit a repository from text
    per-repository output.

- [x] 6. Implement report rendering changes
  - [x] 6.1 Add totals for `dependabot_open_pull_requests` and
    `dependabot_ready_pull_requests`.
  - [x] 6.2 Add plain output labels.
  - [x] 6.3 Add compact table columns.
  - [x] 6.4 Add JSON summary and repository keys.
  - [x] 6.5 Update repository inclusion logic to consider the two new counts.

- [x] 7. Update spec context and final verification
  - [x] 7.1 Update `spec-lite.md` with the implemented behavior summary.
  - [x] 7.2 Run `uv run pytest -v -Werror -Walways`.
  - [x] 7.3 Run `uv run ruff check`.
  - [x] 7.4 Run `uv run ty check src/`.
  - [x] 7.5 Run `uv run ruff format --check`.
