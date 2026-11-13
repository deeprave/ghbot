# Requirements Document

## Introduction

Issue #38 identifies a repository-discovery gap: listing an organisation through GitHub's user endpoint returns public repositories only, even when the authenticated token can access private organisation repositories. Because every command shares discovery, security, issue, information, and drift reports omit those repositories.

## Glossary

- **Owner**: a configured `--owner` value or configured account name.
- **User owner**: a GitHub account whose `type` is `User`.
- **Organisation owner**: a GitHub account whose `type` is `Organization`.
- **Accessible repository**: a repository returned by GitHub for the authenticated token.
- **Discovered repository**: the scanner's owner, raw repository metadata, and resolved owner type.

## Requirements

### Requirement 1: Classify owners before listing repositories

**User Story:** As an operator, I want ghbot to identify whether a configured owner is a user or organisation, so that it uses the correct repository-list endpoint.

#### Acceptance Criteria

1. FOR EACH configured owner, THE discovery service SHALL obtain account metadata from `GET /users/{owner}`.
2. IF the metadata `type` is `Organization`, THEN THE discovery service SHALL list repositories through `GET /orgs/{owner}/repos`.
3. IF the metadata `type` is `User`, THEN THE discovery service SHALL list repositories through `GET /users/{owner}/repos`.
4. THE account lookup and repository listing requests SHALL use `github_api_call()` and `url_vars`.
5. BOTH listing endpoints SHALL request `type=all` and preserve pagination.

### Requirement 2: Expose owner type to processors

**User Story:** As a processor author, I want the resolved owner type available with each discovered repository, so that future functionality can select user or organisation endpoints without repeating owner classification.

#### Acceptance Criteria

1. THE shared scanner SHALL preserve the resolved owner type in each discovered-repository record.
2. THE resolved owner type SHALL be `User`, `Organization`, or `None` when account metadata lacks a recognised type.
3. FOR EACH processor invocation, THE main loop SHALL pass the discovered repository's owner type through a keyword-only `owner_type` argument.
4. THE raw GitHub repository metadata SHALL remain available in the discovered-repository record.
5. EVERY built-in processor constructor and custom processor constructor used with `_main()` SHALL accept `owner_type: str | None = None` as a keyword-only argument.

### Requirement 3: Preserve shared scanning behaviour

**User Story:** As an operator, I want organisation support without changing which processors run or the existing repository filters.

#### Acceptance Criteria

1. FOR EACH accessible private organisation repository returned by GitHub, THE shared scanner SHALL yield the owner and repository to all existing processors.
2. THE scanner SHALL continue to omit archived repositories for user and organisation owners.
3. THE `info`, `issues`, `security`, and `drift` commands SHALL continue to use the shared scanner without command-specific discovery logic.
4. IF no owners are configured, THEN discovery SHALL retain the existing warning and yield no repositories.

### Requirement 4: Error and retry policy

**User Story:** As an operator, I want account classification to follow the same resilient behaviour as repository listing.

#### Acceptance Criteria

1. IF owner metadata or repository listing returns not-found or access-denied, THEN discovery SHALL log a warning and skip that owner.
2. IF owner metadata or repository listing has a non-rate-limit GitHub API failure, THEN discovery SHALL retry the complete discovery attempt once and log an error before skipping the owner if the retry fails.
3. IF a primary or secondary rate-limit error occurs, THEN discovery SHALL propagate it to the existing caller policy.
4. IF the account metadata contains an unrecognised or missing `type`, THEN discovery SHALL log a warning and use the existing user endpoint as a backward-compatible fallback.

### Requirement 5: Changelog

**User Story:** As a maintainer, I want release-visible changes documented, so users and external processor authors can understand new features and API changes.

#### Acceptance Criteria

1. THE repository SHALL contain a root `CHANGELOG.md` using a concise versioned changelog format.
2. THE `0.10.0` entry SHALL describe the `drift` command and its release-drift/PyPI-configuration reporting.
3. THE Unreleased entry SHALL describe the new `owner_type` keyword-only processor argument as a breaking change for custom `RepoProcessor` implementations.
4. THE changelog SHALL state that built-in processors accept `owner_type=None` by default.

## Non-Functional Requirements

- Do not add authentication configuration, API tokens, or new dependencies.
- Preserve async iteration and existing pagination semantics.
- Test user and organisation endpoint selection, private-repository pass-through, archived filtering, and retry/error handling with `AsyncMock` through `uv run`.
- Existing command-line interfaces remain unchanged.
- The keyword-only `owner_type` argument defaults to `None` for built-in processor compatibility; custom `RepoProcessor` implementations must accept it before this change can be adopted.
