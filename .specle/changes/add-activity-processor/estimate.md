# Estimate: activity processor

## T-shirt size

XL

## Breakdown

- New production files: approximately 2–3: an `activity` mode with its processor and collection
  report, plus the packaged activity schema and any schema-registration resource.
- Modified production files: approximately 4–6: mode discovery/CLI wiring, configuration for
  `--since` and `--stale-days`, combo integration, report/schema registration, and documentation.
- Modified test files: approximately 6–8: processor fetch and aggregation behaviour, bounded
  pagination, unavailable metrics, rendering, CLI discovery/options, combo, and schema tests.
- Estimated implementation tasks: 8–10.

## Key risks

- The report combines several independent GitHub domains—commits, branches, releases, pull
  requests, issues, comments, contributors, and workflow runs—each with distinct pagination,
  permission, and empty-result semantics.
- All-time counts and window-bound metrics must remain clearly distinct, particularly for stale
  pull requests, failed workflows, and the default 30-day activity window.
- Dependabot abandonment detection must recognise only a bounded, documented signal and retain no
  unrelated comment content.
- The mode is both independently reportable and combinable, so its plain, table, JSON, schema,
  and combined-report contracts must agree on unavailable versus empty data.

## Confidence

Medium. Existing mode, report, schema, pagination, and partial-result patterns provide useful
extension points, but the exact endpoint/query mix and efficient aggregation need design work.

## Recommendation

Create a technical design before tasks. It should define each metric's source, scope, bounded
pagination, unavailable semantics, and report/schema representation; it should also separate
activity-window data from all-time totals.

## Similar past work

- `issues-ci-report` added a bounded GraphQL pull-request metric set to the issues processor.
- `security-add-severity` extended a report and its versioned schema while preserving nullable
  partial-result semantics.
- `combo-reports` established the discovered-mode collection and combined-report integration.
