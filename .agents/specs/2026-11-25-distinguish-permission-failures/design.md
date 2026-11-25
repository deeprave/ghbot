# Design: distinguish permission failures

## Overview

Introduce explicit unavailable-resource classifications at the GitHub client boundary and preserve
them through processor results, report documents, human rendering, schemas, and explicit-selection
outcomes. The change retains all existing nullable metric keys and rate-limit behaviour. It adds
safe availability metadata and a post-output exit status of 8 when an explicitly selected
repository itself cannot be scanned.

## Architecture

```text
GitHub response
  -> github_api_call() classifies 404, non-rate-limit 403, and rate limits
  -> processor maps endpoint-specific disabled signals and API errors to metric availability
  -> RepoResult carries metric unavailable metadata or explicit repository outcome
  -> collection document/rendering preserves repository result and reason markers
  -> ReportOutcome writes output, then command exits 8 for explicit repository unavailability
```

### Error taxonomy

- Add `GitHubForbiddenError` as a `GitHubApiError` subclass. `github_api_call()` raises it for a
  REST or GraphQL 403 after rate-limit classification has been attempted; a 404 remains
  `GitHubNotFoundError`. GraphQL `FORBIDDEN` response codes receive the same classification.
- Retain the existing primary and secondary rate-limit branches before generic 403 handling, with
  no policy or delay change.
- Add a lightweight unavailable value type (reason plus optional safe message) for report data;
  it is not an exception. Its reasons are `not_found`, `forbidden`, `disabled`, and `error`.
- A processor recognizes `disabled` only from endpoint-specific documented response signals,
  including each security-alert endpoint. Disabled metrics remain unavailable but do not create an
  ordinary fetch error or partial repository status on their own. An ambiguous 404 remains
  `not_found`; it must not be recast as disabled or forbidden.

## Explicit repository discovery and outcomes

`scan_repositories()` continues yielding only discovered repositories for owner scans. For explicit
selections, it yields an explicit-unavailable discovery outcome instead of silently discarding a
missing/forbidden/archived selection. That outcome contains owner, repository, and one of:

| Condition | Status | Reason |
| --- | --- | --- |
| 404 repository lookup | `failed` | `not_found` |
| non-rate-limit 403 lookup | `failed` | `forbidden` |
| archived metadata | `skipped` | `archived` |

The runner converts each outcome into a mode-visible repository result, without constructing a
processor or issuing further requests. Collections retain those entries even when normal report
filters would omit a repository with zero findings. Owner discovery retains its current skip
behaviour for hidden and archived repositories.

## API and data

Extend `RepoResult` with an `unavailable` mapping keyed by metric name. Its serialized shape is:

```json
{
  "dependabot_alerts": null,
  "unavailable": {
    "dependabot_alerts": {
      "reason": "forbidden",
      "message": "Resource not accessible by integration"
    }
  }
}
```

The message is optional. Keep only a safe, concise exception message; never include headers,
tokens, raw response bodies, or private payload data. Processors add an unavailable entry whenever
they assign `null` for an unavailable metric. Existing `null` semantics and normal successful
metrics remain unchanged.

Each current `1.0` report schema gains an optional `unavailable` object whose values require a
reason enum and allow an optional message. Existing schema IDs remain unchanged because 1.0.0 is
unreleased.

## Rendering and exit behaviour

- Add shared formatting for unavailable values: `N/A (<reason>)` in plain and table output, with
  table column widths that accommodate the marker.
- Explicit unavailable repository entries show their status and reason in each applicable report
  representation, including the table repository column and JSON. They are visible in output but
  do not inflate active finding, issue, or drift summaries.
- Drift report eligibility includes a repository with per-metric unavailable metadata, even if it
  has neither positive drift nor a repository-level explicit-outcome reason. Drift summary totals
  continue to count only positive integer commit values.
- Extend `ReportOutcome` with post-write exit metadata. Commands write output first, log a concise
  explicit-repository unavailable summary, and then exit 8 when such an outcome exists.
- A rate-limit abort retains exit 4 and takes precedence over exit 8, preserving current rate-limit
  recovery semantics. Metric-only unavailability does not alter a successful command exit.

## Error handling

| Condition | Client/processor policy | Report policy | Exit |
| --- | --- | --- | --- |
| 404 | `GitHubNotFoundError` | metric `not_found`, or explicit failed repository | 8 only for explicit repository |
| 403 non-rate limit | `GitHubForbiddenError` | metric `forbidden`, or explicit failed repository | 8 only for explicit repository |
| disabled feature | processor maps documented signal | metric `disabled` | 0 |
| archived explicit repository | discovery outcome | explicit skipped repository | 8 |
| ordinary recoverable API error | existing handling plus metric `error` where null | partial/availability metadata | 0 |
| primary/secondary rate limit | unchanged | existing incomplete report | 4 |

## Documentation

README documents the taxonomy, that a 404 can also conceal unavailable private access, reason
markers, and exit 8. It explains that exit 8 means a requested repository’s expected data is
missing even though the report was successfully written.

## Test strategy

- Client tests: REST and GraphQL 404/ordinary 403/`FORBIDDEN`, secondary-limit 403, and unchanged
  primary/secondary handling.
- Discovery/runner tests: explicit missing, forbidden, and archived outcomes; owner-scan omission;
  report-before-exit-8 behaviour.
- Processor and rendering tests: collected disabled and forbidden metric availability tests,
  nullable compatibility, non-partial disabled features, explicit outcome status/reason in aligned
  tables, drift summaries, human reason markers, and safe messages.
- Schema tests: all current report schemas validate unavailable entries and reject invalid reasons.
- Run focused tests first, then `uv run pytest -v -Werror -Walways`, `uv run ruff check`,
  `uv run ty check src/`, and `uv run ruff format --check`.
