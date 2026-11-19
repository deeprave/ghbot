# Technical Design: issues item metadata

## Overview

Extend `ghbot issues` without adding REST calls. The processor will retain item metadata already returned by the open-items REST endpoint, and the existing paginated GraphQL pull-request query will collect the oldest creation timestamp in each author category. JSON gains the fields unconditionally; plain and table rendering only show item creation dates when `--dates` is selected.

## Architecture

```text
REST /repos/{owner}/{repo}/issues?state=open
  -> _item_record()
  -> RepoResult.open_items (normalized metadata)
  -> IssuesCollectionReport.document() / render()

GraphQL open pull requests (each page)
  -> validate connection and PR detail fields
  -> category counters + per-category oldest timestamp + Dependabot detail records
  -> RepoResult pull-request metrics
  -> collection summary / per-repository JSON

Click --dates -> IssuesMode.new_collection(options)
  -> IssuesCollectionReport(dates=True)
  -> plain/table item rendering only
```

The mode continues to own command parsing, processor construction, collection data, and report formatting. `github_api_call()` remains the only API boundary.

## REST item data

`_item_record()` will preserve the current `number`, `title`, `type`, and internal `labels`, then add:

| Normalized key | REST source | Value when absent |
| --- | --- | --- |
| `created_at` | `created_at` | `None` |
| `updated_at` | `updated_at` | `None` |
| `url` | `html_url` | `None` |
| `author` | `user.login` | `None` |
| `draft` | `draft` | `None` for issues; REST value for pull requests |

`_item_json()` will always emit this metadata, regardless of `--labels`; labels retain their existing opt-in JSON behaviour. The processor makes no additional item request.

## Pull-request age metrics and detail

The GraphQL node selection expands to `number`, `author { login }`, `mergeStateStatus`, `createdAt`, `url`, and `isDraft`. `number`, `createdAt`, and `url` must be non-empty values with their expected types; `isDraft` must be boolean. `createdAt` is parsed as an ISO-8601 timestamp before it participates in aggregation. Malformed node data follows the established whole-metrics failure path.

Two keys are added to the existing four count metrics:

```text
oldest_dependabot_pull_request_created_at
oldest_other_pull_request_created_at
```

For each node, category selection remains based on `author.login == "dependabot[bot]"`. The processor compares parsed instants and stores the original GitHub UTC timestamp belonging to the oldest pull request in each category. A category with no pull requests receives `None`.

For every Dependabot node, it also appends this JSON-only detail record in API pagination order:

```json
{
  "number": 15,
  "url": "https://github.com/acme/widgets/pull/15",
  "created_at": "2026-11-01T10:20:30Z",
  "draft": false,
  "merge_ready": true
}
```

`merge_ready` uses the established `mergeStateStatus == "CLEAN"` rule. The list is `[]` when collection succeeds but no Dependabot PRs are open, and `null` when any pull-request metric cannot be collected. It is deliberately not repeated for the `other` category and is not rendered in plain or table reports.

The metric-key constants will distinguish count keys from timestamp keys. On successful collection, per-repository records contain all six scalar values and the Dependabot detail list. On GraphQL API or validation failure, `_record_pull_request_metric_error()` sets all six scalar values and `dependabot_pull_requests` to `None`, preserving the existing all-or-nothing metric contract. Primary and secondary rate-limit errors continue to propagate.

At collection level, count keys retain their existing sum-or-unavailable behaviour. Each oldest timestamp is the earliest non-null timestamp across repositories, unless any repository has unavailable pull-request metrics, in which case it is `None`. `pull_request_metrics_complete` continues to consider the four count metrics: an age value of `None` can also mean a successful category with no pull requests.

## Report rendering and CLI

`IssuesCollectionReport` gains a `dates: bool` option after its existing `results` data field (`labels`, `results`, `dates`). The command adds `--dates`, includes it in its options mapping, and `IssuesMode.new_collection()` passes it into the collection.

JSON item shape, whether or not `--dates` is selected:

```json
{
  "number": 15,
  "title": "Add retry to fetch",
  "type": "pr",
  "created_at": "2026-11-01T10:20:30Z",
  "updated_at": "2026-11-02T11:22:33Z",
  "url": "https://github.com/acme/widgets/pull/15",
  "author": "octocat",
  "draft": false
}
```

When `--dates` is selected, plain item lines include the local `YYYY-MM-DD HH:MM TZ` rendering of `created_at` before the title. The table gains a fixed-width `Created (local)` column immediately before the optional `Labels` column. Parsing converts GitHub's UTC timestamp with the operator's platform-local timezone at render time, including daylight-saving changes where the configured local timezone observes them. Missing or malformed item timestamps render as `N/A`; JSON preserves the original API value. Without `--dates`, both renderers retain their current exact layout. The `--labels` option remains independent and composes with `--dates`.

Summary and per-repository JSON include the two oldest timestamp keys. Human-readable summary and metric blocks do not gain those aggregate values in this increment; `--dates` is intentionally item-focused.

README documentation will describe the always-present JSON metadata, oldest timestamp keys, and `--dates` output option.

## Error handling

| Situation | Behaviour |
| --- | --- |
| Open-items REST 404/inaccessible | Preserve existing `open_item_count=None`, `open_items=None`, and debug event. |
| Open-items recoverable API failure | Preserve existing partial result, error event, and unavailable item values. |
| GraphQL transport/API failure | Mark all six pull-request metrics and the Dependabot detail list unavailable, record one fetch error, and return a partial result. |
| Malformed GraphQL page/node, including invalid detail fields or `createdAt` | Treat as the existing recoverable pull-request-metric failure; mark all six scalar values and the detail list unavailable. |
| Primary or secondary rate limit | Re-raise unchanged to the task-pool policy. |
| Empty author / empty category | Classify no author as `other`; use `author=None` for REST items; retain `None` oldest timestamp for an empty category. |

## Test strategy

- Processor tests: normalized issue and pull-request metadata, missing REST user, GraphQL pagination across categories, ordered Dependabot detail records, oldest values across pages, empty categories, malformed/missing detail fields and timestamps, all-metric unavailability, and unchanged rate-limit propagation.
- Report tests: JSON metadata and Dependabot detail are always present on successful collection; populated metadata values are retained by JSON serialization; timestamps appear in repository and summary JSON; default plain/table layout is unchanged; `--dates`, `--labels`, and both together render correctly against the host platform's local conversion without mutating process timezone state; missing or malformed creation dates render `N/A` only in date-enabled human output.
- Mode tests: Click help exposes `--dates`; all format combinations pass the correct `dates` and `labels` options into `run_mode`.
- Documentation test/update: README examples or field documentation match the output contract.
- Implementation verification uses the project gates through `uv run`: pytest with warnings as errors, Ruff check, ty, and Ruff format check.
