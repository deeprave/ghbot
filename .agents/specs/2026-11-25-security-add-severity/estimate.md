# Estimate: security add severity

## T-shirt size

L

## Breakdown

- New files: 1 (`design.md`; the existing specification artifacts are already present).
- Modified production files: approximately 3 (`security.py`, the security JSON Schema, and
  `README.md`).
- Modified test files: approximately 4 (security processor, report rendering, report mode, and
  schema tests).
- Estimated implementation tasks: 5.

## Key risks

- GitHub's code-scanning payload can supply either a security severity or a non-security fallback;
  classification must retain every alert while not presenting fallback values as security levels.
- A per-repository unavailable metric requires a `null` breakdown, while summaries must retain the
  established partial-availability aggregation semantics and still reconcile with total counts.
- The table already has six metric columns; two compact severity columns must remain legible and
  preserve existing unavailable markers.
- The published schema identifier remains `ghbot://schemas/security/1.0.json`; this is an
  additive, unreleased-1.0 evolution and must validate the exact breakdown shape.

## Confidence

High. Issue #49 specifies the data sources, output contract, and boundary cases. Existing alert
pagination, unavailable handling, aggregation, rendering, and schema tests provide direct
extension points.

## Recommendation

Complete a technical design before tasks. The work touches a public report contract and several
output forms, so implementing from the requirements alone risks mismatched null and aggregation
semantics.

## Similar past work

- `2026-05-06-enhance-security-info` added per-repository and summary security metrics across all
  report forms.
- `2026-11-25-distinguish-permission-failures` established unavailable metric metadata and
  nullable report-schema handling.
