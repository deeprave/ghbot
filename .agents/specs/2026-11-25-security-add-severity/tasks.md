# Implementation Tasks: security add severity

- [x] 1. Define and validate the severity-breakdown report contract (`tests/unit/test_report_schemas.py`, `src/ghbot/schemas/security/1.0.json`)
  - [x] 1.1 Add failing schema tests for nullable complete five-key breakdowns and rejection of missing, extra, or negative values.
  - [x] 1.2 Add the reusable `severity_counts` schema definition and both per-repository and summary fields without changing existing totals or the schema ID.

- [x] 2. Collect Dependabot severity counts from the existing alert listing (`tests/unit/test_security_processor.py`, `src/ghbot/modes/security.py`)
  - [x] 2.1 Add failing processor tests for mixed, missing, unknown, zero, paginated, and unavailable Dependabot alert severities.
  - [x] 2.2 Count each yielded Dependabot alert once, classify `security_advisory.severity`, and set the paired breakdown to `None` whenever the existing total is unavailable.

- [x] 3. Collect code-scanning severity counts from the existing alert listing (`tests/unit/test_security_processor.py`, `src/ghbot/modes/security.py`)
  - [x] 3.1 Add failing processor tests for security severity, missing security severity with `rule.severity` fallback, unknown values, pagination, zero, and unavailable code-scanning alerts.
  - [x] 3.2 Count each yielded code-scanning alert once; prefer `rule.security_severity_level` and place fallback, missing, and unknown values in `other` without changing secret-scanning collection.

- [x] 4. Aggregate and render severity breakdowns (`tests/unit/test_security_report.py`, `tests/unit/test_security_report_mode.py`, `src/ghbot/modes/security.py`)
  - [x] 4.1 Add failing collection and rendering tests for summary reconciliation, partial/all-unavailable aggregation, JSON fields, plain severity lines, compact table columns, and unavailable markers.
  - [x] 4.2 Aggregate available breakdowns with existing total semantics and render the two additive breakdowns while retaining all existing total keys, columns, labels, and activity text.

- [x] 5. Document the public security report fields and complete focused regression coverage (`README.md`, `tests/unit/test_security_processor.py`, `tests/unit/test_security_report.py`)
  - [x] 5.1 Add failing or strengthened regression assertions for the documented field semantics and invariant that every non-null breakdown sums to its paired total.
  - [x] 5.2 Document severity sources, `other`, nullable availability, unchanged totals, and total-only secret scanning; run focused security tests.

- [x] 6. Close verification coverage gaps (`tests/unit/test_security_processor.py`, `tests/unit/test_security_report.py`)
  - [x] 6.1 Add a severity-specific paginated-listing regression test that asserts every yielded alert contributes to the paired total and breakdown.
  - [x] 6.2 Add a table-rendering regression test for compact Dependabot and code-scanning severity values.

- [x] 7. Separate code-scanning security and rule severity (`tests/unit/test_security_processor.py`, `src/ghbot/modes/security.py`)
  - [x] 7.1 Add failing tests for Dependabot `moderate`, security-level classification, and fallback `error`/`warning`/`note` diagnostic classification.
  - [x] 7.2 Normalize `moderate` to `medium` and classify each code-scanning alert into exactly one separate security- or rule-severity breakdown.

- [x] 8. Extend the report contract and rendering (`tests/unit/test_report_schemas.py`, `tests/unit/test_security_report.py`, `src/ghbot/schemas/security/1.0.json`, `src/ghbot/modes/security.py`, `README.md`)
  - [x] 8.1 Add failing schema and labelled plain/table/JSON tests for both code-scanning breakdowns and their combined-total invariant.
  - [x] 8.2 Add the fields, summary aggregation, distinct compact renderings, documentation, and label-bound assertions while retaining existing totals.

- [x] 9. Assert zero-shaped code-scanning breakdowns (`tests/unit/test_security_processor.py`)
  - [x] 9.1 Extend the existing zero-alert processor test to assert both complete all-zero breakdown maps.
