# Requirements Document

## Introduction

ghbot currently discovers repositories by listing every repository for configured owners. Both `run_processor()` and `run_mode()` use the shared discovery path in `runner.py`. Operators also need to scan an explicit, additive set of repositories without owner-based searches. Explicit repository entries may be qualified (`owner/repo`) or bare (`repo`); bare entries are tried for every configured owner.

## Glossary

- **qualified repository**: An `owner/repo` entry that specifies its owner directly.
- **bare repository**: A `repo` entry expanded into an `owner/repo` candidate for every configured owner.
- **explicit selection mode**: Repository discovery mode activated by at least one `--repo` or `--repos` option.
- **repository file**: A file supplied through `--repos` containing explicit repository entries.
- **selection representation**: The ordered, deduplicated `owner/repo` candidate list passed from global CLI configuration to the shared discovery path.

## Requirements

### Requirement 1: Accept inline repository selections

**User Story:** As an operator, I want to provide repositories directly on the command line, so that I can scan a targeted set without listing all repositories for an owner.

#### Acceptance Criteria

1. THE CLI SHALL provide a global repeatable `--repo` option.
2. EACH `--repo` occurrence SHALL accept a comma-separated list of repository entries.
3. FOR EACH bare entry, THE CLI SHALL create an `owner/<entry>` candidate for every configured owner, preserving the configured owner order.
4. IF a qualified entry appears, THEN THE application SHALL create only its specified `owner/repo` candidate.
5. IF a bare entry is supplied without any configured owners, THEN THE CLI SHALL reject the invocation with an actionable usage error.

### Requirement 2: Accept repository-file selections

**User Story:** As an operator, I want to provide repositories from a file, so that large targeted scans are manageable outside the command line.

#### Acceptance Criteria

1. THE CLI SHALL provide a single-use global `--repos FILE` option.
2. EACH repository file SHALL accept repository entries separated by lines or commas.
3. THE parser SHALL ignore empty entries and lines whose first non-whitespace character is `#`.
4. Repository-file entries SHALL support the same qualified and bare forms as `--repo`.
5. A bare repository-file entry SHALL expand using every configured owner, as for `--repo` entries.
6. IF a repository file cannot be read, THEN THE CLI SHALL raise an actionable usage error naming the file.

### Requirement 3: Combine selection sources predictably

**User Story:** As an operator, I want inline and file selections to compose, so that I can combine shared lists with ad-hoc repositories.

#### Acceptance Criteria

1. THE application SHALL treat every `--repo` occurrence and the optional `--repos` file as additive.
2. IF either explicit-selection option is used, THEN the shared discovery path used by both `run_processor()` and `run_mode()` SHALL scan only the resolved explicit repository entries and SHALL NOT perform owner-based repository listing.
3. IF explicit-selection options are absent, THEN the shared discovery path SHALL retain the existing owner-based discovery behaviour.
4. `--owner` SHALL be optional when every explicit repository entry is qualified.
5. `--owner` values that do not resolve a bare explicit repository SHALL NOT independently trigger owner-based discovery in explicit selection mode.
6. THE application SHALL resolve all `--repo` entries before processing the optional `--repos` file; within each source, it SHALL preserve entry order.
7. THE application SHALL deduplicate candidates using a case-folded `owner/repo` key before validation, preserving the first original candidate spelling, logging each duplicate, and skipping it.

### Requirement 4: Validate explicit repositories through the shared scanner

**User Story:** As an operator, I want explicitly named repositories validated before processing, so inaccessible or nonexistent repositories do not cause processor failures.

#### Acceptance Criteria

1. FOR EACH resolved explicit repository, THE shared discovery path SHALL validate it through GitHub's repository endpoint using the configured API token.
2. THE validation path SHALL use `github_api_call()` and parameterized `url_vars`.
3. IF validation finds an accessible repository, THEN THE scanner SHALL yield a `DiscoveredRepository` with its repository metadata and owner type.
4. IF validation returns not-found or access-denied, THEN THE scanner SHALL warn and skip that repository.
5. IF validation has a non-rate-limit GitHub API failure, THEN THE scanner SHALL apply the existing retry-and-skip error policy.
6. IF validation encounters a primary or secondary rate limit, THEN THE scanner SHALL propagate it to the existing caller policy.
7. THE scanner SHALL continue to omit archived repositories from explicit selections.

## Non-Functional Requirements

- `--repo`, `--repos`, and `--owner` remain global options owned by the application shell and work with every command.
- The merged configuration SHALL carry the selection representation to the shared runner; mode modules SHALL NOT parse or select repositories themselves.
- Preserve the shared `DiscoveredRepository` path so processors receive the same owner type and metadata in both selection modes.
- Do not add dependencies or change token authentication behaviour.
- Parse repository specifications without interpreting shell, file, or repository contents as executable code.
- Add focused tests for owner expansion, file parsing, duplicate logging and skipping, explicit-mode suppression of owner listing, validation/error handling, and archive filtering; run them through `uv run`.
