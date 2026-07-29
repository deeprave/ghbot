# Spec Lite: Enhance Security Info

## Problem

The security scanner reports alert counts but not whether Dependabot has already opened
remediation pull requests, or whether those PRs are ready to merge once approval requirements are
ignored.

## Goal

Extend `security` results with:

- `dependabot_open_pull_requests`
- `dependabot_ready_pull_requests`

Ready means the open Dependabot PR is not draft, is not known unmergeable, and all reported commit
statuses and check runs for the PR head commit are passing or non-blocking. Review approval
requirements are ignored.

## Output

Plain, table, and JSON security reports include aggregate and per-repository Dependabot PR counts.
Text reports display unavailable counts as `N/A`; JSON preserves them as `null`.

## Design

- List open PRs with `/repos/{owner}/{repo}/pulls?state=open`.
- Filter to Dependabot-authored PRs, anchored on `dependabot[bot]`.
- For each Dependabot PR, inspect:
  - `/repos/{owner}/{repo}/commits/{ref}/status`
  - `/repos/{owner}/{repo}/commits/{ref}/check-runs`
- Store counts in `RepoResult.results`.
- Preserve existing security processor error policy and progress/output separation.

## Verification

- Passing: `uv run pytest -v -Werror -Walways`
- Passing: `uv run ruff check`
- Passing: `uv run ty check src/`
- Passing: `uv run ruff format --check`

## Implementation Status

Complete. `SecurityRepoProcessor` now records open and ready Dependabot PR counts, and all report
formats include those counts in summaries and per-repository data.

Progress logging reports alert counts and Dependabot PR counts separately, for example
`found alerts 3, dependabot PRs 3`. When only Dependabot PRs are found, the alert-count phrase is
omitted.
