# Requirements: distinguish permission failures

## Introduction

ghbot currently collapses missing repositories, access denial, disabled features, and archived
repositories into absent values or skipped scan entries. Consumers of known repository lists cannot
tell an unavailable result from a genuine absence of findings. This change implements GitHub issue
#50 by preserving those distinctions in exceptions, logs, report results, schemas, and
documentation.

## Glossary

- **not found**: a GitHub 404 response. For private resources it may also conceal missing access.
- **forbidden**: a non-rate-limit GitHub 403 response indicating that the token lacks access.
- **disabled**: a repository feature that GitHub reports as unavailable because it is switched off.
- **archived**: a repository whose metadata identifies it as archived.
- **unavailable**: a per-metric JSON map that records why a metric value is `null`.

## Requirements

### Requirement 1: Classify unavailable GitHub resources

**User Story:** As an operator, I want ghbot to distinguish unavailable causes so I can diagnose
whether a value was absent, inaccessible, or disabled.

#### Acceptance Criteria

1. WHEN GitHub returns a non-rate-limit 403, THE client SHALL raise a distinct forbidden error and
   SHALL NOT classify it as not found.
2. WHEN GitHub returns a 404, THE client SHALL raise a distinct not-found error; documentation
   SHALL state that GitHub may use 404 to conceal private resources from an unauthorized token.
3. WHEN a processor identifies a disabled feature, THE processor SHALL record it as disabled rather
   than not found or forbidden.
4. THE existing primary and secondary rate-limit classifications and recovery behaviour SHALL remain
   unchanged.
5. WHEN a disabled feature is the only recoverable condition for a metric, THE processor SHALL NOT
   classify the repository as partial solely because that feature is disabled.

### Requirement 2: Preserve metric availability in reports

**User Story:** As a report consumer, I want every unavailable metric explained without breaking
existing nullable values.

#### Acceptance Criteria

1. WHEN a metric is unavailable, THE metric value SHALL remain `null` and its repository record
   SHALL contain an `unavailable` entry for that metric.
2. EACH unavailable entry SHALL contain a reason from `not_found`, `forbidden`, `disabled`, or
   `error`, and SHALL include GitHub's safe message when available.
3. Plain and table reports SHALL render unavailable values with a concise reason marker instead of
   an unqualified `N/A`.
4. THE shipped versioned JSON schemas SHALL describe the `unavailable` field and its allowed
   reasons without advancing the unreleased `1.0` schema identifiers.
5. Unavailable or explicit-outcome repository entries SHALL remain visible without contributing to
   summaries of active findings, issues, or drift.
6. WHEN a drift metric is unavailable, THE repository SHALL remain in drift output with its
   availability metadata, without contributing to drift totals.

### Requirement 3: Surface explicitly selected repository outcomes

**User Story:** As an operator scanning a known repository list, I want every selected repository
to appear even when ghbot cannot inspect it.

#### Acceptance Criteria

1. WHEN an explicitly selected repository is not found or forbidden, THE applicable report SHALL
   include a result identifying the repository, a failed status, and the reason.
2. WHEN an explicitly selected repository is archived, THE applicable report SHALL include a result
   identifying the repository, a skipped status, and the archived reason.
3. Owner-based discovery SHALL continue to omit repositories that GitHub does not list or that are
   archived.
4. Logs for explicit repository outcomes SHALL state the repository and classified reason without
   exposing tokens, credentials, response headers, or private payload data.
5. AFTER writing a report that contains any unavailable explicitly selected repository, THE command
   SHALL exit with status 8. This SHALL NOT discard successful results or treat the repository
   outcome as an internal fatal error.
6. Plain and table reports SHALL show an explicit repository outcome's status and reason in every
   applicable representation.

## Non-Functional Requirements

- Use the existing `github_api_call` boundary and project error policy; do not make raw GitHub
  requests outside it.
- Preserve read-only scanning, existing JSON keys, authentication behaviour, and rate-limit
  handling.
- Add deterministic tests for 404, non-rate-limit 403, secondary-limit 403, disabled features,
  archived selections, and explicitly selected missing repositories.
- Update README with the reason taxonomy and 404 ambiguity.
- Document exit status 8: it means expected data from an explicitly selected repository is missing,
  so automation must not treat the report as fully successful even though ghbot wrote it.
- Per-metric `unavailable` metadata remains reportable without changing the command's exit status
  unless the repository itself is unavailable.
- Delivery for this change shall reference `Closes #50` in its pull request.
