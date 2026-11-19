# Issues item metadata

## Problem

The `issues` report does not expose item dates, URLs, authors, or draft state. Its Dependabot and other pull-request metrics also cannot identify or cite the oldest open pull request.

## Goal

Add this metadata to JSON output, add oldest-creation timestamps and detailed Dependabot pull-request records, and offer `--dates` for opt-in local-time human-readable dates.

## Boundaries

- Reuse fields already returned by the REST item listing; no additional REST calls.
- Extend the existing GraphQL pull-request query with `number`, `createdAt`, `url`, and `isDraft`, preserving pagination, malformed-response handling, and rate-limit propagation.
- JSON includes per-repository Dependabot pull-request records; plain and table remain summary-oriented.
- Default plain and table reports stay unchanged; `--dates` renders local date, time, and timezone abbreviation and composes with `--labels`.

## Verification

Test metadata with missing authors and draft items, Dependabot detail records, oldest timestamps for each category, empty and unavailable categories, malformed GraphQL data, local-time rendering, output formats, and option composition. Run all repository Python gates through `uv run`.
