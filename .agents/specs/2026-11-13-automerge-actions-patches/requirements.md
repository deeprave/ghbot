# Requirements Document

## Introduction

The Dependabot auto-merge workflow successfully identifies grouped GitHub Actions patch updates, but only enables auto-merge for `uv` patch updates. GitHub Actions patch updates therefore remain open despite passing the same checks.

## Glossary

- **Dependabot metadata**: The `dependabot/fetch-metadata` outputs used to classify an update.
- **Patch update**: Metadata with `update-type` equal to `version-update:semver-patch`.
- **GitHub Actions update**: Metadata with `package-ecosystem` equal to `github_actions`.

## Requirements

### Requirement 1: Auto-merge GitHub Actions patch updates

**User Story:** As a maintainer, I want passing Dependabot GitHub Actions patch updates to be queued for auto-merge, so routine safe updates do not remain open unnecessarily.

#### Acceptance Criteria

1. IF a Dependabot pull request is a non-draft GitHub Actions patch update, THEN THE auto-merge workflow SHALL generate an app token and enable merge-queue auto-merge.
2. IF a Dependabot pull request is a grouped GitHub Actions patch update, THEN THE workflow SHALL apply the same policy.
3. IF the metadata identifies a GitHub Actions minor or major update, THEN THE workflow SHALL NOT enable auto-merge.

### Requirement 2: Preserve existing policy

**User Story:** As a maintainer, I want the new policy to be narrow, so existing Python dependency handling and Dependabot grouping remain unchanged.

#### Acceptance Criteria

1. THE workflow SHALL continue to enable auto-merge for `uv` patch updates.
2. THE workflow SHALL NOT change Dependabot grouping configuration or action reference pinning.
3. THE workflow SHALL retain app-token authentication for all eligible updates.

## Non-Functional Requirements

- Change only the Dependabot auto-merge workflow and associated spec tracking.
- Do not add static tests for workflow YAML.
- Validate YAML and inspect the workflow conditions directly.
