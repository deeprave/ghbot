# Requirements: Activity processor

## Introduction

ghbot can report repository posture and release drift, but it cannot describe how actively a
repository is being maintained. Maintainers need a compact, comparable view of contribution,
change, pull-request, issue, Dependabot, and workflow activity without confusing that history
with security posture or changes since the most recent release.

## Glossary

- **Activity window**: The period beginning at `--since`, or 30 days before the scan when that
  option is omitted.
- **Default-branch commit count**: The total number of commits reachable from the repository's
  configured default branch.
- **Ignored Dependabot pull request**: A Dependabot pull request closed without merge.
- **Dependabot abandonment notice**: A comment by Dependabot indicating that it has stopped
  monitoring a repository because it is inactive or otherwise unsupported.
- **Stale pull request**: An open pull request with no update for more than the configured stale
  threshold, which defaults to 30 days.
- **Workflow success rate**: The proportion of successful completed runs among the most recent 20
  completed runs in the repository.

## Requirements

### Requirement 1: Provide a standalone activity report

**User Story:** As a maintainer, I want a report that distinguishes current repository activity
from release drift and configuration posture.

#### Acceptance Criteria

1. THE CLI SHALL provide an `activity` mode backed by `ActivityRepoProcessor` using the existing
   repository-selection, authentication, concurrency, partial-result, and exit-code behaviour.
2. THE mode SHALL render plain text by default, table output, and a structured JSON report with
   `--json`; it SHALL support `--output`.
3. THE mode SHALL accept `--since` as an ISO-8601 timestamp for period-bound activity data and
   default its activity window to 30 days before the scan when omitted.
4. THE mode SHALL be reportable and participate in `combo` using the established discovered-mode
   contract.
5. THE JSON report SHALL have a packaged versioned schema available through `ghbot schema`.

### Requirement 2: Report repository change and contributor activity

**User Story:** As a maintainer, I want to identify recently active, dormant, and lightly
maintained repositories.

#### Acceptance Criteria

1. THE report SHALL include the most recent commit timestamp on the default branch and across
   repository branches, plus the total default-branch commit count.
2. THE report SHALL include the latest release tag and its publication timestamp, and the latest
   merged pull request and merge timestamp.
3. THE report SHALL include the count of unique contributors excluding GitHub bot accounts.

### Requirement 3: Report pull-request and issue lifecycle activity

**User Story:** As a maintainer, I want to see backlog age and pull-request lifecycle signals.

#### Acceptance Criteria

1. THE report SHALL include all-time pull-request totals for opened, merged, and closed without
   merge; it SHALL also include the current open count and oldest-open timestamp.
2. THE report SHALL include all-time issue totals for opened and closed, plus the current open
   count and oldest-open timestamp, when issues are enabled.
3. WHEN issues are disabled, THE report SHALL represent issue metrics as unavailable or
   not-applicable rather than zero.
4. THE report SHALL identify open pull requests stale for more than `--stale-days`, which SHALL
   default to 30, including their count and oldest last-activity timestamp.

### Requirement 4: Report Dependabot maintenance signals

**User Story:** As a maintainer, I want to distinguish active Dependabot work from ignored or
abandoned Dependabot maintenance.

#### Acceptance Criteria

1. THE report SHALL count Dependabot pull requests that are open, merged, and closed without
   merge using the shared Dependabot identity rule.
2. THE report SHALL detect and report a Dependabot abandonment notice when Dependabot comments
   that it is no longer monitoring the repository because of inactivity or a materially equivalent
   condition.
3. THE report SHALL identify only the signal and associated pull request metadata; it SHALL NOT
   expose unrelated pull-request comment bodies.

### Requirement 5: Report bounded workflow health

**User Story:** As a maintainer, I want to know whether automation is recently healthy without
retrieving unbounded workflow history.

#### Acceptance Criteria

1. THE report SHALL include the most recent workflow run conclusion and, when that run failed,
   its attempt number.
2. THE report SHALL calculate workflow success rate from the most recent 20 completed runs.
3. THE report SHALL include the timestamp of the most recent successful workflow run.
4. THE report SHALL list or summarise failed workflow runs within the activity window.

### Requirement 6: Preserve resilient reporting semantics

**User Story:** As a maintainer, I want inaccessible activity sources to remain visible as missing
data rather than making the whole report misleading.

#### Acceptance Criteria

1. THE processor SHALL re-raise fatal and rate-limit errors.
2. WHEN an individual activity fetch has a recoverable API failure, THE processor SHALL preserve
   fetched activity data, mark only the affected metrics unavailable, and return a partial result.
3. THE report SHALL distinguish fetched-empty, unavailable, disabled, and failed repository data
   using established report conventions.

## Boundaries

- This report measures activity; it does not replace `drift` release-relative change measurement,
  `issues` operational posture, or `security` finding counts.
- Commit counts are limited to the default branch; they are not repository-wide object counts.
- Workflow history is bounded to 20 completed runs, and no workflow logs or job output is fetched.
- Dependabot detection uses metadata and only recognised abandonment-notice text; it does not
  retain unrelated comment content.
- The report is read-only and does not trigger, rerun, close, merge, or otherwise alter GitHub
  resources.
