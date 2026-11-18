# Requirements Document

## Introduction

The `issues` report currently reduces every open GitHub issue and pull request to a number, title, type, and optional labels. Consumers cannot determine age, link to an item, identify its author, or distinguish draft pull requests. Pull-request summary metrics also lack the age of the oldest open pull request in each category.

## Glossary

- **item**: An open GitHub issue or pull request returned by the existing issues REST listing.
- **item metadata**: Creation and update timestamps, HTML URL, author login, and (for pull requests) draft state.
- **pull-request category**: Dependabot-authored or other open pull requests in the existing GraphQL metrics query.
- **oldest timestamp**: The earliest `createdAt` timestamp in a pull-request category.

## Requirements

### Requirement 1: Preserve item metadata

**User Story:** As an automation consumer, I want each reported item to identify its provenance and age so that I can apply age-based policy and cite it.

#### Acceptance Criteria

1. THE issues JSON document SHALL include `created_at`, `updated_at`, `url`, and `author` for every item.
2. THE issues JSON document SHALL include `draft` for pull-request items and SHALL represent it as `null` for issue items.
3. IF a GitHub item has no user, THEN its `author` value SHALL be `null`.
4. THE command SHALL take these values from the existing REST issue payload and SHALL NOT make additional REST requests for them.
5. Existing item keys and their meanings SHALL remain unchanged.

### Requirement 2: Report pull-request age metrics and Dependabot detail

**User Story:** As an automation consumer, I want age metrics and a detailed Dependabot pull-request list so that I can assess and cite stale maintenance work.

#### Acceptance Criteria

1. THE existing pull-request GraphQL query SHALL request `createdAt`, `url`, and `isDraft` for every returned node.
2. THE per-repository and summary metrics SHALL expose `oldest_dependabot_pull_request_created_at` and `oldest_other_pull_request_created_at`.
3. EACH repository JSON record SHALL include `dependabot_pull_requests`, containing one object per open Dependabot pull request with `number`, `url`, `created_at`, `draft`, and `merge_ready` fields.
4. IF a repository has no open Dependabot pull requests, THEN `dependabot_pull_requests` SHALL be an empty array.
5. IF pull-request metrics are unavailable, THEN `dependabot_pull_requests` and both oldest timestamps SHALL be `null`.
6. Malformed GraphQL data SHALL follow the existing unavailable-metrics policy and SHALL NOT crash the command.
7. Existing GraphQL pagination and rate-limit propagation behaviour SHALL remain unchanged.

### Requirement 3: Keep human output compact by default

**User Story:** As an operator, I want dates when needed without widening normal reports.

#### Acceptance Criteria

1. THE issues command SHALL provide a `--dates` flag.
2. IF `--dates` is supplied, THEN plain and table item output SHALL include each item's creation date and time in the operator's local timezone, including its timezone abbreviation.
3. IF `--dates` is not supplied, THEN existing plain and table item columns and lines SHALL remain unchanged.
4. JSON output SHALL include the new item metadata without requiring `--dates`.
5. THE `--dates` flag SHALL compose with the existing `--labels` option.

## Non-Functional Requirements

- The detailed pull-request list is JSON-only. Do not add it to plain or table output in this increment.
- Add focused async processor, report-rendering, and CLI tests using the project conventions in `.agents/project/testing.md`.
- Keep JSON output additive in preparation for the schema contract in `2026-11-17-versioned-report-schemas`.
- Run repository checks through `uv run` when implementation begins.
