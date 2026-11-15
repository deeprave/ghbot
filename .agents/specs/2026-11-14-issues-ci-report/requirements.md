# Requirements Document

## Introduction

The `issues` command currently reports open issues and pull requests together without distinguishing Dependabot pull requests from other pull requests, or indicating which pull requests GitHub considers ready to merge. Maintainers need those categories and merge-ready counts to prioritise dependency updates separately from other work, without per-pull-request REST status lookups.

## Glossary

- **Dependabot pull request**: An open pull request whose author login is `dependabot[bot]`.
- **other pull request**: Any open pull request not authored by `dependabot[bot]`.
- **merge-ready pull request**: A pull request whose GitHub GraphQL `mergeStateStatus` is `CLEAN`.
- **bulk PR query**: A paginated GraphQL query that retrieves all open pull requests and their author and merge-state fields for one repository.

## Requirements

### Requirement 1: Categorise open pull requests through GraphQL

**User Story:** As a maintainer, I want Dependabot pull requests reported separately from other pull requests, so that I can distinguish dependency-update work from the rest of the backlog.

#### Acceptance Criteria

1. FOR EACH scanned repository, THE issues processor SHALL retrieve all open pull requests through a paginated bulk PR query.
2. FOR EACH returned pull request, THE processor SHALL classify it as either a Dependabot pull request or an other pull request.
3. THE processor SHALL preserve its existing open-issue reporting behaviour and exclude pull requests from the open-issue count.
4. THE processor SHALL record a total count for Dependabot pull requests and a total count for other pull requests.

### Requirement 2: Count merge-ready pull requests

**User Story:** As a maintainer, I want merge-ready counts for each pull-request category, so that I can identify PRs that GitHub considers mergeable with passing commit status.

#### Acceptance Criteria

1. THE processor SHALL record a merge-ready count for Dependabot pull requests and a merge-ready count for other pull requests.
2. THE processor SHALL count a pull request as merge-ready only when its GraphQL `mergeStateStatus` is `CLEAN`.
3. THE processor SHALL NOT derive merge readiness from separate REST combined-status or check-run lookups.
4. THE processor SHALL NOT issue a separate API request for an individual pull request while deriving these four metrics.
5. IF the bulk PR query has a non-rate-limit GitHub API failure, THEN THE processor SHALL mark the repository result partial, record the error, and make all four pull-request metrics unavailable.
6. IF the bulk PR query encounters a rate limit, THEN THE processor SHALL propagate it to the existing caller policy.

### Requirement 3: Render the new metrics consistently

**User Story:** As a maintainer, I want the new counts in every issues-report format, so that scripts and human-readable output agree.

#### Acceptance Criteria

1. THE plain issues report SHALL show Dependabot total and merge-ready counts, and other-pull-request total and merge-ready counts, for each reported repository and in the summary.
2. THE table issues report SHALL include distinct columns for the four pull-request metrics.
3. THE JSON issues report SHALL expose distinct, documented keys for the four pull-request metrics in repository records and the summary.
4. IF any repository's pull-request metrics are unavailable, THEN THE aggregate pull-request metrics SHALL be `N/A`/`null` rather than a partial total, and human-readable reports SHALL notify users that the aggregate is incomplete.
5. THE JSON report SHALL expose whether aggregate pull-request metrics are complete.

## Non-Functional Requirements

- Use a paginated GitHub GraphQL query for pull-request categorisation and merge readiness; do not introduce an N+1 REST lookup pattern.
- Preserve existing issues command options and output/file-writing behaviour.
- Preserve existing shared GitHub API error and rate-limit handling, including distinct primary and secondary GraphQL rate-limit classification.
- Add focused processor and report tests for category separation, `CLEAN` versus non-`CLEAN` states, pagination, unavailable data, and all supported output formats; run them through `uv run`.
