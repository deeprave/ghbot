# Implementation Tasks

- [x] 1. Characterise the existing public report contracts (`tests/unit/test_report.py`, `tests/unit/test_issues_report.py`, `tests/unit/test_drift_report.py`)
  - [x] 1.1 Confirm existing regression assertions cover the current plain, table, and JSON output for security, issues (with and without labels), and drift.
  - [x] 1.2 Confirm output-file errors, unsupported render formats, filtering, ordering, unavailable values, and JSON schemas remain covered before moving implementation code.

- [x] 2. Add cross-mode report styles (`src/ghbot/report_style.py`, `tests/unit/test_report_style.py`)
  - [x] 2.1 Add failing tests for `ReportStyle.from_format`, `PlainReportStyle`, `JSONReportStyle`, `TableColumn`, and Markdown table header/separator/row alignment.
  - [x] 2.2 Implement the styles, `MarkdownTableReportStyle` selection for `table`, JSON document serialization, and the shared stdout/file writer.

- [x] 3. Move the security mode into a cohesive module (`src/ghbot/modes/security.py`, `src/ghbot/processor.py`, `tests/unit/test_security_report_mode.py`)
  - [x] 3.1 Add failing tests for a security mode unit, processor pairing, collection aggregation, summary/filter semantics, partial-result handling, and style rendering.
  - [x] 3.2 Move `SecurityRepoProcessor` with its result interpretation and `SecurityCollectionReport` into the security mode module; export its named mode unit and remove the central implementation.

- [x] 4. Move the issues mode into a cohesive module (`src/ghbot/modes/issues.py`, `src/ghbot/processor.py`, `tests/unit/test_issues_report_mode.py`)
  - [x] 4.1 Add failing tests for the issues mode unit, processor pairing, collection aggregation, labels option, and existing partial/unavailable rendering semantics.
  - [x] 4.2 Move `IssuesRepoProcessor` with its collection report and mode-specific item/summary rendering data into the issues module; export its named mode unit and remove the central implementation.

- [x] 5. Move the drift mode into a cohesive module (`src/ghbot/modes/drift.py`, `src/ghbot/processor.py`, `tests/unit/test_drift_report_mode.py`)
  - [x] 5.1 Add failing tests for the drift mode unit, processor pairing, positive-drift filtering, collection aggregation, and partial PyPI/unavailable rendering.
  - [x] 5.2 Move `DriftRepoProcessor` with its collection report and mode-specific release/drift rendering data into the drift module; export its named mode unit and remove the central implementation.

- [x] 6. Remove the legacy report module (`src/ghbot/report.py`, existing report tests)
  - [x] 6.1 Move report-contract tests to import their owning mode modules and shared style module directly, preserving all existing output assertions.
  - [x] 6.2 Delete `report.py` after the CLI and tests have no remaining imports; do not retain rendering compatibility adapters.

- [x] 7. Wire report commands through resolved mode handlers (`src/ghbot/__main__.py`, `tests/unit/test_main.py`)
  - [x] 7.1 Add failing tests that security, issues, and drift resolve their mode unit before scanning; construct processors through the handler; forward options and owner type; and collect only completed results.
  - [x] 7.2 Implement the handler-first report scan wrapper and command wiring, retaining the processor-only info path and Click format-conflict behaviour.

- [x] 8. Establish collection composition (`src/ghbot/report_style.py`, `tests/unit/test_report_composition.py`)
  - [x] 8.1 Add failing tests for ordered security/issues/drift sections, direct nesting of standalone JSON documents, and exclusion of info.
  - [x] 8.2 Implement the collection composition helper without adding the `combo` CLI command or dynamic discovery.

- [x] 9. Verify and record completion (`spec.md`, `status.json`)
  - [x] 9.1 Refresh the specification and status record with completed task and verification state.
  - [x] 9.2 Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
