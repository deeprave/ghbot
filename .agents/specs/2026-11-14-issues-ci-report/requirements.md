# Requirements Document

## Introduction

The `issues` command currently reports open issues and pull requests together without distinguishing Dependabot pull requests from other pull requests, and without indicating whether their CI checks pass. Maintainers need those categories and their CI-ready counts to prioritise dependency updates separately from other work.

## Glossary

- **Dependabot pull request**: An open pull request whose author login is `dependabot[bot]`.
- **other pull request**: Any open pull request not authored by `dependabot[bot]`.
- **CI-passing pull request**: A pull request whose reported combined commit status and check runs satisfy the project's successful CI criteria.
- **non-CI requirement**: Draft state, merge conflict state, approval/review state, or branch-protection policy; these do not affect the CI-passing count.

## Requirements

### Requirement 1: Categorise open pull requests

**User Story:** As a maintainer, I want Dependabot pull requests reported separately from other pull requests, so that I can distinguish dependency-update work from the rest of the backlog.

#### Acceptance Criteria

1. FOR EACH scanned repository, THE issues processor SHALL classify every open pull request as either a Dependabot pull request or an other pull request.
2. THE processor SHALL preserve its existing open-issue reporting behaviour.
3. THE processor SHALL record a total count for Dependabot pull requests and a total count for other pull requests.
4. THE processor SHALL exclude pull requests from the open-issue count as it does today.

### Requirement 2: Count CI-passing pull requests

**User Story:** As a maintainer, I want CI-passing counts for each pull-request category, so that I can identify PRs that need only non-CI requirements such as review or merge-conflict resolution.

#### Acceptance Criteria

1. FOR EACH open Dependabot pull request, THE processor SHALL determine whether its CI checks pass.
2. FOR EACH open other pull request, THE processor SHALL determine whether its CI checks pass.
3. THE processor SHALL record a CI-passing count for Dependabot pull requests and a CI-passing count for other pull requests.
4. THE CI-passing determination SHALL use the same combined-status and check-run success criteria for both categories.
5. A pull request's draft state, mergeability, approval state, and other non-CI requirements SHALL NOT exclude it from the CI-passing count.
6. IF a status or check-run lookup has a non-rate-limit GitHub API failure, THEN THE processor SHALL mark the repository result partial, record the error, and exclude only the affected pull request from the CI-passing count.
7. IF a status or check-run lookup encounters a rate limit, THEN THE processor SHALL propagate it to the existing caller policy.

### Requirement 3: Render the new metrics consistently

**User Story:** As a maintainer, I want the new counts in every issues-report format, so that scripts and human-readable output agree.

#### Acceptance Criteria

1. THE plain issues report SHALL show Dependabot total and CI-passing counts, and other-pull-request total and CI-passing counts, for each reported repository and in the summary.
2. THE table issues report SHALL include distinct columns for the four pull-request metrics.
3. THE JSON issues report SHALL expose distinct, documented keys for the four pull-request metrics in repository records and the summary.
4. THE report SHALL preserve existing `N/A`/`null` behaviour when pull-request data is unavailable.

## Non-Functional Requirements

- Reuse the existing GitHub API wrapper and parameterized URLs for status and check-run lookups.
- Preserve existing issues command options and output/file-writing behaviour.
- Do not treat approval, mergeability, or draft state as CI results.
- Add focused processor and report tests for category separation, CI-pass/failure/unavailable cases, and all supported output formats; run them through `uv run`.
