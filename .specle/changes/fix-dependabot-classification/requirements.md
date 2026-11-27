# Requirements Document

## Introduction

The issues scan and security scan report Dependabot pull-request statistics. They currently rely on one literal GitHub login representation, `dependabot[bot]`. GitHub GraphQL can instead return `dependabot`, causing issues mode to classify genuine Dependabot pull requests as other pull requests. This makes the issues-mode Dependabot breakdown, readiness counts, ages, and item list unreliable.

## Glossary

- **Dependabot identity**: A GitHub-authored pull request whose login is either `dependabot` or `dependabot[bot]`.
- **Issues mode**: The ghbot mode that collects open issues and pull-request metrics through GitHub GraphQL.
- **Security mode**: The ghbot mode that collects Dependabot pull-request statistics through GitHub REST endpoints.

## Requirements

### Requirement 1: Classify GitHub Dependabot identities consistently

**User Story:** As a maintainer, I want Dependabot statistics to remain accurate regardless of the GitHub API representation used by a scan.

#### Acceptance Criteria

1. WHEN a pull request author login is `dependabot` or `dependabot[bot]`, THE system SHALL classify the pull request as Dependabot.
2. WHEN a pull request author login is any other value or is absent, THE system SHALL classify the pull request as other.
3. THE issues mode and security mode SHALL use the same Dependabot identity rule rather than maintaining independent literal comparisons.
4. WHEN a security-mode REST pull request has a missing, null, or non-object `user` payload, THE system SHALL classify it as other without failing the repository scan.

### Requirement 2: Report accurate issues-mode Dependabot metrics

**User Story:** As a maintainer, I want the issues report's Dependabot and other pull-request metrics to describe the same classification shown in its item details.

#### Acceptance Criteria

1. WHEN GraphQL returns a Dependabot login of `dependabot`, THE issues mode SHALL include the pull request in Dependabot open and merge-ready counts, the Dependabot oldest-date metric, and the Dependabot pull-request list.
2. WHEN a Dependabot pull request has `mergeStateStatus: CLEAN`, THE issues mode SHALL include it in the Dependabot merge-ready count.
3. THE existing issues JSON keys, table columns, and human-readable labels SHALL remain unchanged.

## Boundaries

- This change corrects identity classification only; it does not change GitHub query shape, merge-readiness semantics, report schemas, or output names.
- The recognised identities are the two exact GitHub representations above. The system SHALL NOT use a broad substring or prefix match.
