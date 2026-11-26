# Security alert severity breakdowns

## Problem

Security reports expose only aggregate alert counts, so downstream health checks cannot distinguish
critical risk from low-severity volume.

## Goal

Keep existing totals and add nullable severity data from the existing paginated listings; no new
API requests. Dependabot has one security-severity breakdown. Code scanning separates security
severity from the scanner's diagnostic rule severity. Secret scanning remains total-only.

## Contract

Each repository and summary gain `dependabot_alerts_by_severity`,
`code_scanning_alerts_by_security_severity`, and `code_scanning_alerts_by_rule_severity`.
Security breakdowns contain `critical`, `high`, `medium`, `low`, and `other`; rule breakdowns
contain `error`, `warning`, `note`, and `other`. Each code-scanning alert contributes to exactly
one of its two breakdowns, preserving the existing total. Normalize Dependabot `moderate` to
`medium`. Unavailable breakdowns are `null`; a genuine zero has zero counts.

JSON is additive and schemas validate the new fields. Plain output shows per-repository severity;
tables use a readable compact representation such as `C/H/M/L`. Existing totals, unavailable
semantics, API error policy, rate-limit behaviour, and secret-scanning reporting do not change.

## Verification

Test mixed, missing, unknown, and fallback severities; zero and unavailable metrics; pagination;
summary aggregation; JSON, plain/table rendering; schema validation; and README documentation.

Source context: GitHub issue #49.
