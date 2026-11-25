# Distinguish permission failures

## Problem

ghbot currently represents missing repositories, permission denial, disabled features, and archived
repositories as indistinguishable `null`/`N/A` values or silently omits explicitly selected
repositories.

## Goal

Classify unavailable GitHub resources precisely and preserve that reason in logs and report output.
Keep nullable metric values compatible while adding an `unavailable` map with safe reason/message
metadata. Explicit repository selections must produce failed or skipped report results instead of
disappearing, with their status and reason in every report representation. Unavailable entries stay
visible but do not inflate active summaries; metric-level drift failures remain visible without
adding to drift totals.

## Contract

The client distinguishes REST and GraphQL `not_found`, `forbidden`, disabled features, and rate limits. Reports use
`unavailable[metric] = {reason, message?}` alongside `null` values. Explicit missing/forbidden
repositories are failed; explicit archived repositories are skipped. After writing a report with
one of those unavailable explicit repositories, the command exits 8 so automation recognizes that
expected data is missing. Owner discovery remains unchanged. Schemas remain at the unreleased
`1.0` IDs.

## Design direction

Add exception types at the GitHub client boundary, translate them into per-metric availability
metadata in processors, and carry explicit discovery outcomes into report collections. Recognize
documented disabled security features without making the result partial. Render aligned reason and
status markers in human output; update schemas and README. Test response classification,
processor/report propagation, summaries, and explicit-selection outcomes without live GitHub calls.

## Verification

Run focused exception, processor, report, schema, and explicit-selection tests, followed by the
full pytest, Ruff, Ty, and formatting gates through `uv run`.
