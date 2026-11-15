# Combo reports

## Problem

Running `security`, `issues`, and `drift` independently repeats repository discovery and produces separate output documents.

## Goal

Add `combo`, a meta-processor that performs one shared repository scan and runs the three reportable processors per repository. `info` is intentionally excluded.

## Design

The command groups each processor's `RepoResult` values after shared discovery and renders them with existing report renderers. Repository-level work remains bounded by the existing task pool; each reportable processor receives the same discovery context. Partial results remain isolated to their processor.

## Output

- JSON: one object with `security`, `issues`, and `drift` report documents, each retaining its standalone schema.
- Plain and table: labelled security, issues, and drift sections in order, each preserving its standalone lines, rows, and columns.
- Existing format flags and output-file support apply to the combined report.

## Verification

Test one shared scan, security/issues/drift execution, `info` exclusion, result grouping, output sections, JSON nesting, format validation, and file writing. Run all Python gates through `uv run`.
