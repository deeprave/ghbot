# Requirements Document

## Introduction

Release publication must be an intentional manual operation from the current `main` commit. The existing workflow is driven by a published GitHub Release, which means the GitHub Release exists before PyPI publication and repeats the test matrix already completed by normal validation.

## Glossary

- **Release workflow**: `.github/workflows/python-release-publish.yml`.
- **Release commit**: the exact commit on `main` selected when the workflow is manually dispatched.
- **Validation run**: a successful `Validate` workflow run for the release commit.
- **Package version**: the version declared in `pyproject.toml` under `[project]`.

## Requirements

### Requirement 1: Manual, main-only invocation

**User Story:** As a maintainer, I want releases to be a deliberate action from `main`, so a release cannot be created by publishing a GitHub Release first.

#### Acceptance Criteria

1. THE release workflow SHALL be invoked only by `workflow_dispatch`.
2. THE release workflow SHALL NOT be triggered by GitHub `release` events.
3. IF a dispatch targets anything other than the `main` branch, THEN THE workflow SHALL fail before publishing or creating a GitHub Release.

### Requirement 2: Validated release commit

**User Story:** As a maintainer, I want release publication to reuse completed CI evidence instead of running a redundant test matrix.

#### Acceptance Criteria

1. THE workflow SHALL verify that `Validate` has a successful completed run for the exact release commit on `main`.
2. IF no such validation run exists, THEN THE workflow SHALL fail before building, publishing, or creating a GitHub Release.
3. THE workflow SHALL NOT run pytest, Ruff, ty, or a release-specific test matrix.
4. THE workflow SHALL check out and build the exact release commit.

### Requirement 3: Versioned publication and release creation

**User Story:** As a maintainer, I want the package metadata to define the release version and a successful publication to create its matching GitHub Release.

#### Acceptance Criteria

1. THE workflow SHALL read the package version from `pyproject.toml`.
2. THE workflow SHALL derive the GitHub release tag as `v<package-version>`.
3. THE workflow SHALL build and publish the package to PyPI through existing trusted publishing.
4. IF PyPI publication fails, THEN THE workflow SHALL NOT create a GitHub Release.
5. AFTER successful PyPI publication, THE workflow SHALL create a GitHub Release for the derived tag targeting the exact release commit.
6. THE release-creation job SHALL have only the permissions required to create the GitHub Release; PyPI publication SHALL retain only its OIDC permission.

## Non-Functional Requirements

- The workflow shall use pinned GitHub Actions consistent with the repository's existing workflows.
- No package registry token shall be added; PyPI uses trusted publishing.
- Local verification commands run through `uv run`.
- The existing `Validate` workflow and its Python matrix remain the source of test coverage.
