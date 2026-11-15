# Requirements Document

## Introduction

`report.py` currently combines mode-specific result interpretation, summary calculations, and plain/table/JSON formatting functions, while the matching processors live separately in `processor.py`. Scanning and reporting are selected independently by command code, so a report mode cannot be maintained as one cohesive component. Refactor each reportable mode around a co-located processor, handler, and collection report; extract only cross-mode output-format behaviour into reusable styles while preserving existing output behaviour.

## Glossary

- **mode handler**: A component co-located with one reportable processor that constructs and owns that mode's collection report.
- **collection report**: A report object that accepts per-repository results during scanning and renders only after the collection is complete.
- **report style**: A reusable formatting strategy selected from the CLI output format.
- **table style**: The base style supplying columns, widths, alignment, headers, and rows.
- **Markdown table style**: The existing `--table` behaviour, implemented as a table-style specialization that emits Markdown tables.

## Requirements

### Requirement 1: Couple reportable processors with collection reports

**User Story:** As a maintainer, I want each reportable processor paired with its collection report, so that scanning, result interpretation, and report-specific data evolve together.

#### Acceptance Criteria

1. THE reporting architecture SHALL provide a mode module for each reportable mode: security, issues, and drift.
2. EACH mode module SHALL co-locate its `RepoProcessor`, mode handler, collection report, result interpretation, and mode-specific summary/render data.
3. EACH mode handler SHALL accept that mode's per-repository results during the shared scan and SHALL construct its collection-level report data.
4. EACH collection report SHALL render only after all relevant repository results have been collected, so that summaries retain their current collection-wide semantics.
5. THE CLI SHALL resolve the mode handler before processing repositories rather than independently selecting a processor and a top-level report function after scanning.
6. THE refactor SHALL preserve `info` as a non-reporting processor.
7. A partial repository result from one mode SHALL remain represented according to that mode's existing report semantics.
8. EACH mode module SHALL expose one named mode unit with its processor and handler contract, so a future scanner can discover reportable modes without a central mode-to-component registry.
9. THE refactor SHALL delete `report.py` and SHALL not retain compatibility adapters or legacy rendering entry points.

### Requirement 2: Introduce reusable report styles

**User Story:** As a maintainer, I want output-format behaviour in reusable style objects, so that mode handlers define report data rather than reimplement formatting details.

#### Acceptance Criteria

1. THE architecture SHALL define a `ReportStyle` base type with a factory that resolves the CLI format selection.
2. THE architecture SHALL provide `PlainReportStyle`, `TableReportStyle`, and `JSONReportStyle` implementations.
3. THE table-style abstraction SHALL provide reusable helpers for column names, widths, justification, headers, and rows.
4. THE JSON-style abstraction SHALL provide reusable helpers for report-document and schema construction.
5. THE existing `--table` selection SHALL resolve to a `MarkdownTableReportStyle` specialization of `TableReportStyle` and SHALL preserve the current Markdown table output.
6. THE refactor SHALL introduce no separate Markdown CLI format or flag.

### Requirement 3: Preserve existing standalone report contracts

**User Story:** As an operator and automation author, I want the refactor to preserve established command outputs, so that internal architecture changes do not break scripts or documentation.

#### Acceptance Criteria

1. THE `security`, `issues`, and `drift` commands SHALL retain their current format flags, default plain output, output-file behaviour, and format-conflict errors.
2. FOR EACH existing supported command and format, THE rendered output and JSON schema SHALL remain behaviourally equivalent to the pre-refactor contract.
3. THE refactor SHALL preserve existing summary calculations, repository filtering, ordering, unavailable-data rendering, and error reporting.
4. THE refactor SHALL not add API calls or alter processor execution semantics.

### Requirement 4: Support report composition

**User Story:** As a maintainer, I want handlers and styles to compose, so that the `combo` command can reuse them without duplicating formatting logic.

#### Acceptance Criteria

1. THE handler and style interfaces SHALL permit a combined report to contain security, issues, and drift collection reports.
2. A combined JSON report SHALL be able to embed each handler's existing JSON document without schema conversion.
3. A combined plain or Markdown-table report SHALL be able to render ordered labelled sections while each handler retains ownership of its report data and style use.
4. THE composition mechanism SHALL not require `InfoRepoProcessor` reporting.

## Non-Functional Requirements

- Move mode-specific reporting out of `report.py` and delete that module once its CLI and test callers use the mode modules directly.
- Keep cross-mode report-style helpers separate from mode modules and do not add dependencies.
- Establish a static mode-unit contract only; dynamic mode discovery is deferred to a future scanner change.
- Prefer clear type-safe interfaces over a mode/format conditional matrix.
- Add regression tests across all existing report modes and formats before removing legacy functions.
- Run the full Python gates through `uv run` and preserve the current public CLI documentation.
