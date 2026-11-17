# Issues item metadata

## Problem

The `issues` report does not expose item dates, URLs, authors, or draft state. Its Dependabot and other pull-request metrics also cannot identify the oldest open pull request.

## Goal

Add this metadata to JSON output, add oldest-creation timestamps to the existing pull-request categories, and offer `--dates` for compact opt-in human-readable dates.

## Boundaries

- Reuse fields already returned by the REST item listing; no additional REST calls.
- Extend the existing GraphQL pull-request query with `createdAt`, `url`, and `isDraft`, preserving pagination, malformed-response handling, and rate-limit propagation.
- Do not add a per-pull-request detail list in this increment.
- Default plain and table reports stay unchanged; JSON is always enriched and `--dates` composes with `--labels`.

## Verification

Test metadata with missing authors and draft items, oldest timestamps for each category, empty and unavailable categories, malformed GraphQL data, output formats, and option composition. Run all repository Python gates through `uv run`.
