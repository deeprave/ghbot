# Requirements Document

## Introduction

Provide a `drift` command that identifies repositories which have a published, stable GitHub release and commits on their configured default branch that are newer than that release. The report helps maintainers spot unreleased changes, including security updates, and highlights repositories whose GitHub Actions workflows indicate that they publish to PyPI.

Pre-releases and draft releases do not establish the release baseline. PyPI status is configuration detection only: the command does not contact PyPI or assert that an upload succeeded.

## Glossary

- **Release baseline**: the latest published, non-prerelease GitHub release returned by GitHub's latest-release endpoint.
- **Release drift**: the number of commits on a repository's default branch that are ahead of its release baseline.
- **Eligible repository**: a repository with a release baseline.
- **Reportable repository**: an eligible repository whose release drift is greater than zero.
- **PyPI configured**: a repository with a workflow whose name or contents contain a recognized PyPI-publishing signal.

## Requirements

### Requirement 1: Repository eligibility and drift

**User Story:** As a maintainer, I want to see only repositories that have unreleased default-branch changes, so I can prioritize releases.

#### Acceptance Criteria

1. THE `drift` command SHALL scan repositories discovered for the configured owners through the existing repository-scanning path.
2. FOR EACH repository, THE processor SHALL obtain the latest published stable GitHub release using `GET /repos/{owner}/{repo}/releases/latest`.
3. IF GitHub reports no latest release, THEN THE processor SHALL treat the repository as ineligible, complete successfully, and omit it from the per-repository report.
4. THE processor SHALL use the repository's configured default branch, and SHALL NOT assume that the branch is named `main`.
5. FOR EACH eligible repository, THE processor SHALL use GitHub's compare endpoint with the release tag as the base and the default branch as the head.
6. THE processor SHALL record GitHub's `ahead_by` value as `commits_since_release`.
7. IF `commits_since_release` is zero, THEN THE repository SHALL be omitted from the per-repository report.
8. IF `commits_since_release` is greater than zero, THEN THE repository SHALL be included in the report with its owner, repository name, default branch, latest-release tag, release publication time, and commit count.

### Requirement 2: PyPI workflow signal

**User Story:** As a maintainer, I want a PyPI indicator on unreleased repositories, so I can distinguish releases that may require package publication.

#### Acceptance Criteria

1. FOR EACH reportable repository, THE processor SHALL inspect the default-branch GitHub Actions workflow files under `.github/workflows/`.
2. THE processor SHALL set `pypi_publishing_configured` to `true` when a workflow name, filename, or workflow content contains a PyPI publication signal, including `pypi`, `pypa/gh-action-pypi-publish`, or a `pypi.org` upload reference.
3. THE processor SHALL set `pypi_publishing_configured` to `false` when accessible workflow files contain no PyPI publication signal.
4. THE processor SHALL NOT query PyPI, infer publication from a GitHub release asset, or claim that a package was published.
5. IF workflow discovery or workflow-file retrieval fails after a repository has been found reportable, THEN THE processor SHALL retain the repository in the report, set `pypi_publishing_configured` to `null`, and record a partial-result diagnostic.

### Requirement 3: Command and report formats

**User Story:** As a CLI user, I want consistent human-readable and machine-readable drift reports.

#### Acceptance Criteria

1. THE CLI SHALL provide a `drift` subcommand with mutually exclusive `--plain`, `--table`, and `--json` flags and an optional `--output` file path.
2. THE default output format SHALL be plain text.
3. THE plain and table reports SHALL show only reportable repositories, sorted by `owner/repository`.
4. THE JSON report SHALL expose a summary and only reportable repositories, with the keys `repository`, `default_branch`, `latest_release_tag`, `latest_release_published_at`, `commits_since_release`, and `pypi_publishing_configured`.
5. ALL formats SHALL include a summary of scanned repositories, released repositories, reportable repositories, and the total commits since release across reportable repositories.
6. THE report renderer SHALL use `N/A` in plain and table output for an unknown PyPI configuration result, and `null` in JSON.

### Requirement 4: Integration and error policy

**User Story:** As an operator, I want drift scanning to preserve the service's established authentication, concurrency, and failure behavior.

#### Acceptance Criteria

1. THE `DriftRepoProcessor` SHALL satisfy the existing `RepoProcessor` protocol and be submitted through the existing `TaskPool`.
2. THE command SHALL use the existing GitHub CLI token retrieval and shared async GitHub client; it SHALL NOT add a token setting or make an unauthenticated PyPI request.
3. THE processor SHALL wrap every GitHub request with `github_api_call()` and use `url_vars` for owner, repository, tag/compare, branch, and blob identifiers.
4. IF GitHub returns a primary or secondary rate-limit error, THEN THE processor SHALL re-raise it for existing `TaskPool` handling.
5. IF metadata or compare retrieval fails with another GitHub API error, THEN THE processor SHALL return a partial result and omit the repository from the per-repository report because its drift cannot be determined.
6. Existing `info`, `security`, and `issues` command behavior SHALL remain unchanged.

## Non-Functional Requirements

- All I/O remains async and runs through the existing bounded-concurrency `TaskPool`.
- GitHub endpoints use the existing `github_api_call()` boundary; no token is logged, persisted, or added to configuration.
- Python tooling and tests run through `uv run`.
