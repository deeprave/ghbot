# Issues report: PR categories and merge-ready counts

## Problem

The `issues` report combines all open pull requests and does not show the category or merge-ready state of Dependabot and other PRs.

## Goal

Report four metrics per repository and in the summary:

1. Dependabot PR total
2. Dependabot merge-ready PRs
3. Other PR total
4. Other merge-ready PRs

## Design constraints

Retrieve open pull requests through a paginated GraphQL query containing each PR author and `mergeStateStatus`. Reject malformed pagination, including an empty or repeated continuation cursor. Classify `dependabot[bot]` separately; count a PR as merge-ready only when its merge state is `CLEAN`. Do not issue individual pull-request, combined-status, or check-run REST requests.

Keep existing open-issue reporting unchanged and exclude pull requests from the issue count. On a non-rate-limit bulk-query failure, mark the repository partial, record the error, and make all four PR metrics unavailable. Propagate primary and secondary rate limits through their existing distinct policies, gathering structured codes from every GraphQL error entry and narrowly recognising the documented secondary-limit signal only as fallback.

Render the four metrics in plain, table, and JSON output while preserving `N/A`/`null` behaviour and existing CLI/output-file behaviour. If any repository metric is unavailable, show aggregate metrics as unavailable and notify human readers; JSON reports `pull_request_metrics_complete`.

## Verification

Test pagination, author classification, `CLEAN` versus non-`CLEAN`, API-error and rate-limit behaviour, unavailable metrics, and all supported report formats. Run project gates through `uv run`.
