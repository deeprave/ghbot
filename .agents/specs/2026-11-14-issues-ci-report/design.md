# Technical Design: Issues PR categories and merge-ready counts

## Overview

Extend the `issues` mode with four pull-request metrics, reported per repository and in the aggregate summary:

| Key | Meaning |
| --- | --- |
| `dependabot_open_pull_requests` | Open PRs authored by `dependabot[bot]`. |
| `dependabot_merge_ready_pull_requests` | Dependabot PRs whose `mergeStateStatus` is `CLEAN`. |
| `other_open_pull_requests` | All other open PRs. |
| `other_merge_ready_pull_requests` | Other PRs whose `mergeStateStatus` is `CLEAN`. |

The existing REST issues query remains responsible for issue records and their current item-level report. A separate, paginated GraphQL pull-request query supplies only the new category and merge-ready metrics. This avoids individual pull-request, status, and check-run API calls.

## Architecture

```text
IssuesRepoProcessor.run()
 ├─ _fetch_open_items()                         existing REST pagination
 │   └─ open_item_count / open_items            unchanged
 └─ _fetch_open_pull_request_metrics()          new GraphQL pagination
     ├─ graphql(open PR query, after=cursor)
     ├─ classify author login
     ├─ count only mergeStateStatus == CLEAN
     └─ write four result keys, or mark all unavailable

IssuesCollectionReport
 ├─ document()                                  JSON records and summary
 ├─ _summary()                                  aggregate available metrics
 ├─ _summary_lines()                            plain and table summary
 └─ table/plain repository rendering            shows four metrics
```

`IssuesRepoProcessor` remains the mode-owned processor. The shared `GitHubClient` protocol gains a `graphql()` method matching the installed GidgetHub client. `github_api_call()` remains the only client-error translation boundary.

## GraphQL API and pagination

The processor defines one static query:

```graphql
query OpenPullRequests($owner: String!, $repo: String!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, states: OPEN, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { author { login } mergeStateStatus }
    }
  }
}
```

For each repository, `_fetch_open_pull_request_metrics()` starts with `after=None`, invokes `await gh.graphql(query, owner=..., repo=..., after=...)` inside `github_api_call()`, processes each page, and continues with `pageInfo.endCursor` only while `hasNextPage` is true. It performs one request per GraphQL page, never one request per PR.

An absent or non-mapping `repository`, `pullRequests`, `pageInfo`, or `nodes` payload is a recoverable malformed API response. The processor records it as an API failure rather than treating it as an empty result. A continuation page must provide a non-empty cursor that has not been used for an earlier continuation; otherwise processing stops as a recoverable failure rather than looping.

Classification uses the exact author login `dependabot[bot]`; a missing or different author is an other PR. A PR contributes to its category total regardless of merge state. It contributes to that category’s merge-ready total only when `mergeStateStatus == "CLEAN"`; `HAS_HOOKS` and every other value do not count.

## Result data and aggregation

On a successful bulk query, the processor writes all four integer keys to `RepoResult.results`. The existing `open_item_count` continues to mean the count returned by the existing issues endpoint, and `_type_total(..., "issue")` continues to produce the open-issue summary without PRs.

On unavailable pull-request metrics, all four result keys are `None`. If any scanned repository has an unavailable pull-request metric, its aggregate is `None`; the report does not present a partial sum as complete. The summary also exposes `pull_request_metrics_complete` so JSON consumers can identify this state directly.

`IssuesCollectionReport.document()` adds the four keys to every repository record and to `summary`, with `None` encoded as JSON `null`.

## Error handling

| Condition | Processor behaviour |
| --- | --- |
| Successful GraphQL page sequence | Store all four integer metrics. |
| `GitHubPrimaryRateLimitError` or `GitHubSecondaryRateLimitError` | Re-raise to the shared runner policy. |
| Any other `FatalError` | Re-raise to the synchronous command boundary. |
| Recoverable GraphQL/API failure or malformed payload | Send `FeedbackEvent("fetch", "error", ...)`, append a result error, set all four metrics to `None`; `run()` returns `partial`. |

`github_api_call()` is extended to translate GidgetHub GraphQL exceptions into the existing error hierarchy. It gathers structured codes from every valid GraphQL error entry: those codes and the client's rate-limit state identify primary limits, while structured secondary-limit codes identify secondary limits. When a response has no structured secondary code, a narrowly recognised GitHub secondary-limit signal is the fallback; arbitrary query-error text must not be promoted to a rate-limit failure. HTTP 429 also identifies a secondary limit. Other GraphQL failures become `GitHubApiError`. This keeps GraphQL traffic subject to the same processor policy as REST traffic without promoting arbitrary query-error text to a rate-limit failure.

## Report rendering

Plain output adds two category lines to the existing summary:

```text
Dependabot PRs:             3
Dependabot merge-ready PRs: 2
Other PRs:                  5
Other merge-ready PRs:      1
```

Each displayed repository block also includes the same four values. `N/A` is shown when a repository value is unavailable.

The table keeps one row per existing issue/PR item and adds four repository-metric columns: `Dependabot PRs`, `Dependabot ready`, `Other PRs`, and `Other ready`. Values repeat for a repository’s item rows, preserving the current item-oriented table contract. Unavailable values display as `N/A`.

JSON exposes the four documented result keys and `pull_request_metrics_complete` in `summary`, and the four metric keys in every repository record. Numeric values remain JSON numbers; unavailable values are `null`. Human-readable summary output adds `Pull-request metrics unavailable: incomplete repository data` when aggregation is incomplete. Existing item records and the `--labels` option are unchanged.

## Test strategy

Add focused unit coverage in the existing issues-mode test modules for:

- GraphQL query variables and multi-page cursor traversal, including a repeated-cursor malformed response, with no status/check-run or per-PR REST calls.
- Dependabot and other classification, including missing authors.
- `CLEAN` counting and non-counting of `HAS_HOOKS`, `BLOCKED`, `DIRTY`, `DRAFT`, `UNKNOWN`, and missing states.
- Recoverable GraphQL error and malformed payload: four unavailable metrics, fetch-error event, result error, and `partial` status.
- Primary and secondary rate-limit propagation for GraphQL failures.
- Plain, table, and JSON rendering of all four metrics, including summary aggregation and `N/A`/`null` values.
- Client-boundary translation for GraphQL exceptions, including structured primary and secondary rate-limit classification from later error entries, the narrow secondary-limit fallback, and non-rate errors whose messages merely contain rate-limit wording.

Run the required quality gates through `uv run`:

```bash
uv run pytest -v -Werror -Walways
uv run ruff check
uv run ty check src/
uv run ruff format --check
```
