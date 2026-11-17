# Combo reports

## Problem

Running `security`, `issues`, and `drift` independently repeats repository discovery and produces separate output documents.

## Goal

Add `combo`, a meta-processor that performs one shared repository scan and runs every discovered
combinable mode per repository. `info` is intentionally excluded because it is non-combinable.

## Design

The command obtains its modes from `combinable_modes()`, builds each mode's collection, groups its
`RepoResult` values after shared discovery, and renders them with `CombinedCollectionReport`.
Repository-level work remains bounded by the existing task pool; each processor receives the same
discovery context. Partial results remain isolated to their processor. Per-repository results are
staged until every mode completes, so a `TaskPool` retry cannot duplicate earlier results. Current
built-ins produce the canonical `drift`, `issues`, and `security` sections without a static
registry.

Configured owners are case-insensitively deduplicated in first-seen order before discovery and
bare-repository expansion. The shared task pool also preserves non-rate-limit fatal processor
errors through to the command boundary on both initial and secondary-limit retry attempts; GitHub
rate-limit classification and retry policy remain unchanged.

## Output

- JSON: one object keyed by each selected mode's canonical name; each nested document retains its
  standalone schema.
- Plain and table: labelled canonical-order sections, each preserving its standalone lines, rows,
  and columns.
- Existing format flags, `--labels` for the issues section, and output-file support apply to the
  combined report.

## Verification

Test one shared scan, discovery-derived execution, `info` exclusion, result grouping, canonical
output sections, JSON nesting, format validation, issues-label forwarding, and file writing. Run
all Python gates through `uv run`. Cover real-task-pool fatal propagation and duplicate owner
normalisation, including a fatal error after a secondary-limit retry.
