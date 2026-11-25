# Design: security add severity

## Overview

Extend existing Dependabot and code-scanning alert pagination to count severity while each alert is yielded. Existing totals remain unchanged. Add two nullable breakdowns to each repository and report summary, then render them in JSON, plain, and table reports. Secret-scanning stays total-only. No endpoints or pagination loops are added.

## Architecture

```text
SecurityRepoProcessor.run()
  |- Dependabot getiter(): increment total and classify security_advisory.severity
  |- Code-scanning getiter(): increment total and classify rule.security_severity_level
  `- Secret-scanning getiter(): unchanged total only

SecurityCollectionReport -> aggregate totals and breakdowns -> JSON/plain/table
```

## Data model and classification

Every available breakdown has this fixed shape:

```python
{"critical": 0, "high": 0, "medium": 0, "low": 0, "other": 0}
```

The total and breakdown increment in the same `getiter()` loop. A helper maps a source value to a known security severity or `other`.

| Source | Classification |
| --- | --- |
| Dependabot `security_advisory.severity` is known | that severity |
| Dependabot severity missing or unknown | `other` |
| Code scanning `rule.security_severity_level` is known | that severity |
| Code scanning security severity missing | `rule.severity` is recorded as `other` |
| Code scanning fallback missing or unknown | `other` |

`error`, `warning`, and `note` are never presented as security severities. The public aggregate bucket is `other`, as proposed in issue #49.

Repository keys:

```text
dependabot_alerts                 int | null       # unchanged
dependabot_alerts_by_severity     SeverityCounts | null
code_scanning_alerts              int | null       # unchanged
code_scanning_alerts_by_severity  SeverityCounts | null
```

Each available breakdown sums to its paired total. Any fetch failure, unavailable feature, or inaccessible endpoint sets both paired values to `None`; the existing `record_unavailable()` remains attached to the total key. An empty listing produces zero and an all-zero breakdown.

## Summary aggregation

Add a helper with the same availability policy as `_total()`: return `None` if every repository has `None`; otherwise begin at the fixed zero shape and add every available breakdown. This ignores unavailable repositories exactly as total aggregation does. Every non-null summary breakdown thus sums to its existing summary total, including a partial scan.

## Report contract and rendering

The security 1.0 schema gains a reusable nullable `severity_counts` definition. When present it has exactly five required non-negative integer keys. Add both breakdown fields to the summary and repository definitions. Retain `ghbot://schemas/security/1.0.json`: this is an additive unreleased-1.0 evolution.

```json
{
  "dependabot_alerts": 7,
  "dependabot_alerts_by_severity": {"critical": 0, "high": 2, "medium": 4, "low": 1, "other": 0},
  "code_scanning_alerts": 3,
  "code_scanning_alerts_by_severity": {"critical": 0, "high": 1, "medium": 1, "low": 0, "other": 1}
}
```

Plain reports retain total lines and add indented severity lines below the corresponding Dependabot and code-scanning values; summaries add matching aggregate lines. Unavailable breakdowns use the same marker as totals.

Tables retain existing columns and add `Dep Sev` and `Scan Sev`, each using `C0 H2 M4 L1 O0` or the established unavailable marker. This fits the existing 16-character metric width for normal counts.

README documents the fields, source values, `other`, null semantics, and total-only secret scans.

## Error handling

| Condition | Behaviour |
| --- | --- |
| 404 or forbidden endpoint | Existing unavailable policy; total and paired breakdown are `null` |
| Disabled feature | Existing disabled policy; total and paired breakdown are `null` |
| Recoverable API error | Existing partial-result policy; total and paired breakdown are `null` |
| Primary or secondary rate limit | Re-raise unchanged |
| Malformed or unknown severity | Count the alert under `other` |

## Test strategy

- Processor tests: mixed known severities, missing severity, unknown severity, `rule.severity` fallback, all-zero listings, pagination, and paired unavailable values.
- Collection tests: multi-repository summary aggregation, partial availability, all unavailable, and breakdown-total invariants.
- Rendering tests: JSON, plain per-repository and summary lines, compact table columns, and unavailable markers.
- Schema tests: nullable and zero-valued breakdowns; reject missing keys, negative counts, extra keys, and invalid values.
- Confirm README matches the public contract, then run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.

## Review revision: separate code-scanning sources

This section supersedes the earlier single `code_scanning_alerts_by_severity` design. Preserve the
existing `code_scanning_alerts` total and add two nullable breakdowns:

```text
code_scanning_alerts_by_security_severity  # critical/high/medium/low/other
code_scanning_alerts_by_rule_severity      # error/warning/note/other
```

If `rule.security_severity_level` is present, count the alert only in the security breakdown;
unknown supplied security values use `other`. If it is absent, count `rule.severity` only in the
rule breakdown, with missing or unknown values in its `other`. Thus the two breakdown sums equal
the unchanged code-scanning total. Normalize Dependabot `moderate` to the existing `medium`
bucket. All paired breakdowns are null when their metric is unavailable and zero-shaped on an
empty listing.

Add matching summary/schema/README fields and distinct plain/table labels (`Scan Sec`, `Scan
Rule`). Tests must bind each rendered value to its label/column, cover `moderate`, and cover the
combined-total invariant.
