# Implementation Tasks

- [x] 1. Preserve REST item metadata in normalized records (`tests/unit/test_issues_processor.py`, `src/ghbot/modes/issues.py`)
  - [x] 1.1 Add failing processor tests for creation/update timestamps, URLs, authors, pull-request draft state, missing users, and issue `draft=None`, confirming no extra REST request is made.
  - [x] 1.2 Extend `_item_record()` to retain the metadata from the existing open-items payload while preserving the current keys and label handling.

- [x] 2. Collect pull-request age metrics and Dependabot detail (`tests/unit/test_issues_processor.py`, `src/ghbot/modes/issues.py`)
  - [x] 2.1 Add failing async tests for the expanded GraphQL selection, multi-page oldest timestamps, ordered Dependabot detail records, empty categories, malformed detail fields/timestamps, unavailable results, and rate-limit propagation.
  - [x] 2.2 Extend the paginated GraphQL query and aggregation to produce both oldest timestamp metrics and JSON-only Dependabot records with `number`, `url`, `created_at`, `draft`, and `merge_ready`.
  - [x] 2.3 Preserve the all-or-nothing failure policy by making all six scalar PR metrics and `dependabot_pull_requests` unavailable together after recoverable API or malformed-response failures.

- [x] 3. Expose the additive JSON contract (`tests/unit/test_issues_report.py`, `src/ghbot/modes/issues.py`)
  - [x] 3.1 Add failing report tests for always-present item metadata, per-repository Dependabot detail, empty versus unavailable detail lists, and oldest timestamp aggregation across available and unavailable repositories.
  - [x] 3.2 Update `IssuesCollectionReport.document()` and summary helpers to emit the metadata, detail list, and oldest timestamp keys while retaining existing count semantics and labels gating.

- [x] 4. Render local item dates on demand (`tests/unit/test_issues_report.py`, `src/ghbot/modes/issues.py`)
  - [x] 4.1 Add failing deterministic rendering tests for AEST/AEDT conversion, missing or malformed timestamps, unchanged default plain/table layouts, and composition with `--labels`.
  - [x] 4.2 Add local-time formatting for `--dates` plain lines and the `Created (local)` table column without rendering Dependabot detail or aggregate oldest timestamps in human-readable formats.

- [x] 5. Wire the command option and document the contract (`tests/unit/test_issues_report_mode.py`, `src/ghbot/modes/issues.py`, `README.md`)
  - [x] 5.1 Add failing mode tests for `--dates` help and propagation alongside each output format and `--labels`.
  - [x] 5.2 Add the Click option and collection option plumbing, then document JSON item metadata, Dependabot detail records, oldest timestamp keys, and local-time `--dates` output.

- [x] 6. Make local-date tests platform-portable (`tests/unit/test_issues_report.py`)
  - [x] 6.1 Remove process-wide timezone mutation and assert `--dates` rendering against the host platform's local conversion.

- [x] 7. Complete the JSON contract coverage and synopsis (`tests/unit/test_issues_report.py`, `README.md`)
  - [x] 7.1 Assert populated item `created_at`, `updated_at`, `url`, and `draft` values survive JSON serialization.
  - [x] 7.2 Update the `--json` synopsis to include oldest timestamp metrics and Dependabot detail records.

- [x] 8. Keep the report data field ahead of the `dates` display option (`src/ghbot/modes/issues.py`)
  - [x] 8.1 Order `IssuesCollectionReport` fields as `labels`, `results`, and `dates`; retain keyword construction at every internal call site.
