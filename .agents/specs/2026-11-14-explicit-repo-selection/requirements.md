# Requirements Document

## Introduction

ghbot currently discovers repositories by listing every repository for configured owners. Operators also need to scan an explicit, additive set of repositories without owner-based searches. Explicit repository entries may be qualified (`owner/repo`) or bare (`repo`), and bare entries inherit the most recently supplied `--owner` context.

## Glossary

- **qualified repository**: An `owner/repo` entry that specifies its owner directly.
- **bare repository**: A `repo` entry that inherits the active owner context.
- **active owner context**: The most recently encountered `--owner` value in CLI argument order.
- **explicit selection mode**: Repository discovery mode activated by at least one `--repo` or `--repos` option.
- **repository file**: A file supplied through `--repos` containing explicit repository entries.

## Requirements

### Requirement 1: Accept ordered inline repository selections

**User Story:** As an operator, I want to provide repositories directly on the command line, so that I can scan a targeted set without listing all repositories for an owner.

#### Acceptance Criteria

1. THE CLI SHALL provide a global repeatable `--repo` option.
2. EACH `--repo` occurrence SHALL accept a comma-separated list of repository entries.
3. THE CLI SHALL preserve the relative order of `--owner` and `--repo` occurrences when resolving bare repository entries.
4. IF a bare entry follows `--owner xyz`, THEN THE application SHALL resolve it as `xyz/<entry>` until a later `--owner` establishes a new active owner context.
5. IF a qualified entry appears, THEN THE application SHALL use its specified owner and SHALL NOT change the active owner context.
6. IF a bare entry occurs before any `--owner` context, THEN THE CLI SHALL reject the invocation with an actionable usage error.

### Requirement 2: Accept repository-file selections

**User Story:** As an operator, I want to provide repositories from a file, so that large targeted scans are manageable outside the command line.

#### Acceptance Criteria

1. THE CLI SHALL provide a global repeatable `--repos FILE` option.
2. EACH repository file SHALL accept repository entries separated by lines or commas.
3. THE parser SHALL ignore empty entries and lines whose first non-whitespace character is `#`.
4. Repository-file entries SHALL support the same qualified and bare forms as `--repo`.
5. A bare repository-file entry SHALL inherit the active owner context at the corresponding `--repos` option's position in CLI argument order.
6. IF a repository file cannot be read, THEN THE CLI SHALL raise an actionable usage error naming the file.

### Requirement 3: Combine selection sources predictably

**User Story:** As an operator, I want inline and file selections to compose, so that I can combine shared lists with ad-hoc repositories.

#### Acceptance Criteria

1. THE application SHALL treat every `--repo` and `--repos` occurrence as additive.
2. IF either explicit-selection option is used, THEN THE application SHALL scan only the resolved explicit repository entries and SHALL NOT perform owner-based repository listing.
3. IF explicit-selection options are absent, THEN THE application SHALL retain the existing owner-based discovery behaviour.
4. `--owner` SHALL be optional when every explicit repository entry is qualified.
5. `--owner` values that do not resolve a bare explicit repository SHALL NOT independently trigger owner-based discovery in explicit selection mode.

### Requirement 4: Validate explicit repositories through the shared scanner

**User Story:** As an operator, I want explicitly named repositories validated before processing, so inaccessible or nonexistent repositories do not cause processor failures.

#### Acceptance Criteria

1. FOR EACH resolved explicit repository, THE scanner SHALL validate it through GitHub's repository endpoint using the configured API token.
2. THE validation path SHALL use `github_api_call()` and parameterized `url_vars`.
3. IF validation finds an accessible repository, THEN THE scanner SHALL yield a `DiscoveredRepository` with its repository metadata and owner type.
4. IF validation returns not-found or access-denied, THEN THE scanner SHALL warn and skip that repository.
5. IF validation has a non-rate-limit GitHub API failure, THEN THE scanner SHALL apply the existing retry-and-skip error policy.
6. IF validation encounters a primary or secondary rate limit, THEN THE scanner SHALL propagate it to the existing caller policy.
7. THE scanner SHALL continue to omit archived repositories from explicit selections.

## Non-Functional Requirements

- `--repo`, `--repos`, and `--owner` remain global options and work with every command.
- Preserve the shared `DiscoveredRepository` path so processors receive the same owner type and metadata in both selection modes.
- Do not add dependencies or change token authentication behaviour.
- Parse repository specifications without interpreting shell, file, or repository contents as executable code.
- Add focused tests for ordered owner context, file parsing, explicit-mode suppression of owner listing, validation/error handling, and archive filtering; run them through `uv run`.
