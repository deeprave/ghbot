# Technical Design: report styles and mode handlers

## Overview

Each reportable mode becomes a cohesive component: its repository processor, handler, collection
report, summaries, result interpretation, and mode-specific render data live together. Shared
output mechanics move to report-style classes. `report.py` is deleted once the CLI and tests use
the mode modules directly.

## Architecture

```text
src/ghbot/
  processor.py          RepoResult, RepoProcessor/Monitor protocols, LoggingMonitor, InfoRepoProcessor
  report_style.py       ReportStyle factory, Plain/Table/MarkdownTable/JSON styles, TableColumn, writer
  modes/
    security.py         SecurityRepoProcessor + SecurityModeHandler + SecurityCollectionReport
    issues.py           IssuesRepoProcessor + IssuesModeHandler + IssuesCollectionReport
    drift.py            DriftRepoProcessor + DriftModeHandler + DriftCollectionReport
```

```text
click command -> resolve its ModeHandler and ReportStyle -> _run_report()
  -> handler.new_collection(options)
  -> discover repository -> handler.new_processor(...)
  -> TaskPool.submit(_collect_result, processor, collection)
       -> processor.run() -> collection.add(result)
  -> pool exits -> collection.render(style) -> write_report()
```

The handler is resolved before scanning. `InfoRepoProcessor` stays on the existing processor-only
path and has no handler. `_collect_result` adds only returned results; it has no await after `add`,
so asyncio task completion cannot interleave a partial update. TaskPool retry, abort, result, and
error behaviour remain unchanged.

## Mode components

Each mode module exports its processor and one handler. The handler constructs a fresh collection
for an invocation and constructs that module's processor for each discovered repository. The
collection owns `list[RepoResult]`, mode summaries, filtering, ordering, detail records, and its
JSON document.

Each module also exports one named mode unit (for example `MODE`) carrying the mode name and its
handler contract. The CLI may import those units explicitly for this change, but no central
mode-to-processor/report registry is introduced. That stable, self-contained export is the
boundary a future scanner will use for dynamic discovery.

| Mode | Human output | JSON output | Options |
| --- | --- | --- | --- |
| Security | active repositories, sorted | all scanned repositories | none |
| Issues | repositories with open items, sorted | all scanned repositories | labels |
| Drift | positive drift, sorted | positive drift only | none |

Partial results, errors, missing keys, and `None` retain each mode's existing semantics. Handlers
do not catch or reinterpret processor failures.

`report.py` is deleted. The CLI imports named mode units directly, and report tests exercise
collections and styles through their owning modules. ghbot does not provide a Python reporting API,
so retaining legacy rendering functions would be unused compatibility surface.

## Shared styles

`ReportStyle.from_format()` resolves `plain`, `table`, and `json`.

```text
ReportStyle
├── PlainReportStyle
├── TableReportStyle
│   └── MarkdownTableReportStyle   # selected by --table
└── JSONReportStyle
```

`TableColumn` holds heading, width, and justification. `TableReportStyle` provides reusable header,
separator, and padded-row helpers. `MarkdownTableReportStyle` emits the existing pipe-delimited
table shape. `JSONReportStyle` serializes a collection-owned document using the existing indentation
and trailing newline; it never changes mode schemas. The shared writer preserves stdout, UTF-8 file
output, and `OSError` to `click.ClickException` conversion. No Markdown flag is added.

## Composition

Every collection exposes `document()` and `render(style)`. A later combo implementation can retain
ordered security, issues, and drift collections. JSON nests their `document()` mappings directly;
plain and table output join labelled sections by calling each collection with the chosen style.
Info cannot be composed because it has no handler.

## API and error handling

No GitHub API calls, endpoints, processor result keys, or processor error policy change. A returned
success or partial result is collected once. A fatal/rate-limit or task failure is not collected and
continues through TaskPool's existing policy. Invalid adapter formats raise `ValueError`; output
write failures raise `click.ClickException`.

## Migration and tests

1. Extract cross-mode styles and the writer into `report_style.py`.
2. Move each reportable processor with its report model into its mode module, updating internal
   imports to use the new owners.
3. Export one named mode unit from each mode module, wire commands through those units, update
   report tests to import their owning modules, and delete `report.py`.
4. Retain regression tests for all existing plain/table/JSON outputs, labels, filtering, ordering,
   unavailable values, schemas, and output files.
5. Add tests for style factory/table helpers, handler processor pairing and collection aggregation,
   handler-first CLI scans with owner type/options, and prebuilt collection composition.
6. Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and
   `uv run ruff format --check` during verification.
