# Requirements: security add severity

## Introduction

`ghbot security` currently exposes only total Dependabot, code-scanning, and secret-scanning alert
counts. Consumers cannot distinguish a critical alert from many low-severity alerts, preventing
severity-based repository health policies. This change adds severity breakdowns without changing
the existing totals or adding GitHub API requests.

## Glossary

- **security-severity breakdown**: counts for `critical`, `high`, `medium`, `low`, and `other`.
- **rule-severity breakdown**: code-scanning diagnostic counts for `error`, `warning`, `note`, and
  `other`.
- **known security severity**: `critical`, `high`, `medium`, or `low`.
- **fallback severity**: a code-scanning rule's `severity` when its security severity is absent.
- **unavailable**: a metric that could not be collected and is represented as `null` with the
  existing availability metadata.

## Requirements

### Requirement 1: Per-repository severity data

**User Story:** As a downstream health-report consumer, I want per-repository alert counts by
severity so that I can apply meaningful risk thresholds.

#### Acceptance Criteria

1. WHEN Dependabot alerts are collected, THE security processor SHALL publish
   `dependabot_alerts_by_severity` with counts for known security severities and `other`.
2. WHEN code-scanning alerts are collected, THE security processor SHALL publish separate
   `code_scanning_alerts_by_security_severity` and `code_scanning_alerts_by_rule_severity`
   breakdowns.
3. WHEN a code-scanning alert has `rule.security_severity_level`, THE processor SHALL classify it
   using that value.
4. WHEN a code-scanning alert has no `rule.security_severity_level`, THE processor SHALL classify
   `rule.severity` as `error`, `warning`, `note`, or `other` in the rule-severity breakdown and
   SHALL NOT present it as a security severity.
5. WHEN GitHub supplies a missing or unrecognised severity, THE processor SHALL count it as
   `other` and SHALL NOT discard the alert.
6. FOR every available Dependabot metric, its security-severity breakdown SHALL equal its total;
   FOR every available code-scanning metric, its security- and rule-severity breakdowns combined
   SHALL equal `code_scanning_alerts`.
7. WHEN Dependabot reports `moderate`, THE processor SHALL normalize it to `medium`.
8. WHEN an alert total is `null` because collection is unavailable, THE corresponding severity
   breakdown SHALL be `null`; WHEN the total is zero, its breakdown SHALL contain zero for every
   defined severity key.
9. THE processor SHALL derive breakdowns from the existing paginated alert listings and SHALL NOT
   make extra GitHub API calls.

### Requirement 2: Report contract and rendering

**User Story:** As a CLI user, I want severity information in every report form while retaining
the existing totals, so that I can assess risk interactively or through automation.

#### Acceptance Criteria

1. THE JSON report SHALL retain the existing total keys and their meanings unchanged.
2. THE JSON report SHALL add nullable `dependabot_alerts_by_severity`,
   `code_scanning_alerts_by_security_severity`, and `code_scanning_alerts_by_rule_severity` fields
   to each repository result and matching aggregate summary totals.
3. Plain output SHALL render the severity breakdown for each repository with available alert data.
4. Table output SHALL render distinct compact security- and rule-severity values while keeping the
   default table readable; `C/H/M/L/O` and `E/W/N/O` representations are permitted.
5. WHEN a breakdown is unavailable, human-readable output SHALL distinguish it from a zero-alert
   breakdown using the established unavailable rendering.
6. Secret-scanning reporting SHALL remain total-only because GitHub supplies no alert severity for
   that endpoint.

### Requirement 3: Schemas, documentation, and verification

**User Story:** As an integrator, I want schemas, documentation, and tests to define the new
fields reliably.

#### Acceptance Criteria

1. THE security JSON Schema SHALL validate the new nullable breakdown fields and reject malformed
   counts or unknown keys for each breakdown type.
2. README documentation SHALL describe the new fields, supported severity sources, `other`, and
   the unchanged secret-scanning total.
3. Tests SHALL cover `moderate`, mixed/unknown security severities, rule `error`/`warning`/`note`,
   zero totals, unavailable collection, pagination, JSON, labelled plain/table output, summaries,
   and schema validation.

## Non-Functional Requirements

- All GitHub calls SHALL remain inside `github_api_call()` and continue to use paginated iterators.
- Existing error, rate-limit, unavailable-metric, and permission-failure behaviour SHALL remain
  unchanged.
- The change SHALL be additive and preserve compatibility for consumers of existing total fields.
- Required verification runs through `uv run`: pytest with warnings as errors, Ruff check, ty
  check, and Ruff format check.
