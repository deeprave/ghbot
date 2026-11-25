# Security alert severity breakdowns

## Problem

Security reports expose only aggregate alert counts, so downstream health checks cannot distinguish
critical risk from low-severity volume.

## Goal

Keep existing totals and add nullable per-severity breakdowns for Dependabot and code-scanning
alerts. Use the alert data already fetched through the existing paginated listings; no new API
requests. Secret scanning remains total-only.

## Contract

Each repository and the report summary gain `dependabot_alerts_by_severity` and
`code_scanning_alerts_by_severity`. Available breakdowns contain `critical`, `high`, `medium`,
`low`, and `other`; their counts sum to the existing total. Unknown or missing severity and
code-scanning's non-security fallback severity are counted as `other`. If a total is unavailable,
its breakdown is `null`; a genuine zero has every count at zero.

JSON is additive and schemas validate the new fields. Plain output shows per-repository severity;
tables use a readable compact representation such as `C/H/M/L`. Existing totals, unavailable
semantics, API error policy, rate-limit behaviour, and secret-scanning reporting do not change.

## Verification

Test mixed, missing, unknown, and fallback severities; zero and unavailable metrics; pagination;
summary aggregation; JSON, plain/table rendering; schema validation; and README documentation.

Source context: GitHub issue #49.
