# Report styles and mode handlers

## Problem

`report.py` separates mode-specific reporting from its matching processor, while also mixing those three modes with plain, table, and JSON formatting. Commands select a processor and separately invoke a report function after scanning, making each mode harder to maintain and composition difficult.

## Goal

Move each reportable mode into a cohesive module containing its processor, handler, and collection report. Handlers accept per-repository results during scanning and render once after the collection completes. Use reusable report styles, selected by a `ReportStyle` factory from the CLI format, only for cross-mode formatting mechanics.

## Architecture

- Security, issues, and drift each have a mode module that owns its processor, handler, collection report, result interpretation, summaries, and report data.
- `PlainReportStyle`, `TableReportStyle`, and `JSONReportStyle` live outside the mode modules and own reusable output mechanics only.
- `MarkdownTableReportStyle` specializes table output and remains the existing `--table` behaviour; no new Markdown flag is introduced.
- `info` remains non-reporting.
- `combo` composes handler-owned collection reports rather than duplicating mode logic.
- Each mode module exports one named mode unit, forming the future dynamic-discovery boundary; discovery itself is not part of this change.
- `report.py` is deleted; the CLI and tests use mode units directly, with no legacy rendering API retained.

## Compatibility

Standalone security, issues, and drift CLI options, output files, summaries, ordering, text, tables, and JSON schemas remain equivalent. Processor execution and API calls do not change.

## Verification

Add regression coverage for all current report commands and formats, style factory selection, handler aggregation, and combo composition. Run all Python gates with `uv run`.
