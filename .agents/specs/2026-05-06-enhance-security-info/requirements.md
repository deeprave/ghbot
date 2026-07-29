# Requirements Document

## Introduction

The `security` command currently reports open Dependabot vulnerability alerts, code scanning
alerts, and secret scanning alerts. Operators also need to understand the remediation pipeline:
how many open Dependabot pull requests already exist, and how many of those pull requests are
ready to merge from a checks perspective.

This feature extends `SecurityRepoProcessor` and the final security report with two additional
per-repository counts:

- open Dependabot pull requests
- open Dependabot pull requests whose checks are passing and are therefore ready for merge except
  for approval requirements

Approval requirements are intentionally ignored. A Dependabot PR that is blocked only by required
reviews should still count as ready when all reported status checks and check runs are passing.

## Glossary

- **Dependabot_PR**: An open pull request authored by Dependabot. The primary identifier is
  `user.login == "dependabot[bot]"`; equivalent Dependabot bot identities may be accepted if the
  GitHub payload clearly identifies the Dependabot bot.
- **Open_Dependabot_PR_Count**: The number of open Dependabot pull requests in a repository.
- **Passing_Dependabot_PR_Count**: The number of open Dependabot pull requests that are ready for
  merge after ignoring approval requirements.
- **Checks_Ready**: A pull request state where all reported commit status contexts and GitHub
  Actions check runs for the PR head commit are successful or otherwise non-blocking.
- **Non_Blocking_Check_Conclusion**: A check run conclusion that should not block readiness:
  `"success"`, `"neutral"`, or `"skipped"`.
- **Blocking_Check_State**: A status context or check run state indicating the PR is not ready:
  pending, queued, in progress, failure, error, cancelled, timed out, action required, startup
  failure, or any unknown non-success state.

## Requirements

### Requirement 1: Count open Dependabot pull requests

**User Story:** As an operator, I want to know how many open Dependabot pull requests exist per
repository, so that I can distinguish unresolved alerts from remediation PRs that already exist.

#### Acceptance Criteria

1. THE `SecurityRepoProcessor` SHALL fetch open pull requests for each scanned repository.
2. THE fetch SHALL use the existing GitHub API wrapper path and SHALL NOT make raw HTTP calls.
3. THE fetch SHALL request only open pull requests.
4. THE processor SHALL count only pull requests authored by Dependabot.
5. THE processor SHALL store the count under `dependabot_open_pull_requests`.
6. IF the pull request endpoint returns 403 or 404, THEN the count SHALL be `None` and no processor
   error SHALL be recorded.
7. IF the pull request endpoint raises a non-fatal `GitHubApiError`, THEN the count SHALL be
   `None`, an error SHALL be recorded, and the result status SHALL become `"partial"`.

### Requirement 2: Count Dependabot pull requests ready for merge

**User Story:** As an operator, I want to know how many open Dependabot pull requests are ready for
merge except for approval requirements, so that I can identify remediation work that can be merged
without waiting for CI or other automated checks.

#### Acceptance Criteria

1. FOR each open Dependabot pull request, THE processor SHALL inspect the PR head commit's reported
   commit status contexts and GitHub check runs.
2. THE processor SHALL store the ready count under `dependabot_ready_pull_requests`.
3. A Dependabot PR SHALL count as ready when all reported status contexts are `"success"` and all
   reported check runs have conclusions in `"success"`, `"neutral"`, or `"skipped"`.
4. A Dependabot PR SHALL NOT count as ready when any status context is pending, failure, error, or
   unknown.
5. A Dependabot PR SHALL NOT count as ready when any check run is queued, in progress, waiting,
   requested, pending, failure, cancelled, timed out, action required, startup failure, or unknown.
6. A Dependabot PR SHALL NOT count as ready when the PR is a draft.
7. A Dependabot PR SHOULD NOT count as ready when GitHub reports `mergeable` as `false`.
8. Approval state, requested reviewers, and required-review branch protection SHALL NOT affect the
   ready count.
9. IF a PR has no reported status contexts and no reported check runs, THEN it SHALL count as ready
   when it is otherwise mergeable and not a draft.
10. IF status or check-run inspection fails for an individual Dependabot PR with a non-fatal
    `GitHubApiError`, THEN that PR SHALL NOT count as ready, the repository result SHALL become
    `"partial"`, and the error SHALL identify the failing readiness check.
11. Fatal errors SHALL be re-raised following the existing processor error policy.

### Requirement 3: Include Dependabot PR counts in all report formats

**User Story:** As an operator, I want the new Dependabot PR counts in plain, table, and JSON
output, so that human and automated consumers receive the same security remediation signal.

#### Acceptance Criteria

1. THE plain report summary SHALL include aggregate `Dependabot PRs` and `Dependabot PRs ready`
   counts.
2. THE plain per-repository section SHALL include `Dependabot PRs` and `Dependabot PRs ready`.
3. THE table report SHALL include columns for open Dependabot PRs and ready Dependabot PRs.
4. THE JSON summary SHALL include `dependabot_open_pull_requests` and
   `dependabot_ready_pull_requests`.
5. EACH JSON repository object SHALL include `dependabot_open_pull_requests` and
   `dependabot_ready_pull_requests`.
6. Text reports SHALL display `None` counts as `"N/A"` and zero counts as `0`.
7. JSON output SHALL preserve `None` counts as JSON `null`.

### Requirement 4: Preserve report inclusion and progress behavior

**User Story:** As an operator, I want the new counts to help identify repositories with actionable
Dependabot PRs without making clean repositories noisy during scanning.

#### Acceptance Criteria

1. A repository with non-zero open Dependabot PRs SHALL be treated as having security activity for
   report inclusion, even when alert counts are zero.
2. A repository with non-zero ready Dependabot PRs SHALL be treated as having security activity for
   report inclusion, even when alert counts are zero.
3. A repository where all alert and Dependabot PR counts are zero SHALL be omitted from plain and
   table per-repository sections.
4. A repository where all alert and Dependabot PR counts are `None` SHALL be omitted from plain and
   table per-repository sections.
5. JSON output SHALL continue to include every scanned repository.
6. Security progress output SHALL continue to reveal repository-specific progress only for
   repositories with non-zero alert or Dependabot PR activity.
7. Security progress output SHALL report alert counts and Dependabot PR counts separately because
   Dependabot PRs can overlap with the underlying alerts.
8. WHEN a repository has Dependabot PR activity but no open alerts, THEN the progress output SHALL
   omit the alert-count phrase.

## Non-Functional Requirements

- No new dependencies.
- All GitHub API access SHALL go through `github_api_call`.
- URL construction SHALL use `url_vars`, not f-strings.
- All Python commands SHALL be run through `uv run`.
- Existing output controls (`--plain`, `--table`, `--json`, `--output`) SHALL keep their current
  behavior.
