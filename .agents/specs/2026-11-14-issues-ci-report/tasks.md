# Implementation Tasks

## 1. Extend the shared GraphQL client boundary

- [x] 1.1 Add unit tests that exercise `github_api_call()` with GidgetHub GraphQL exceptions, including ordinary query failures and primary-rate-limit failures. (Files: `tests/unit/test_client.py`.)
- [x] 1.2 Extend `github_api_call()` to normalize GraphQL exceptions into the existing `GitHubApiError` and `GitHubPrimaryRateLimitError` hierarchy. (Files: `src/ghbot/github/client.py`.)
- [x] 1.3 Add `graphql()` to the processor-facing GitHub client protocol with the installed client’s query-and-variable shape. (Files: `src/ghbot/processor.py`.)

## 2. Collect bulk pull-request metrics in the issues processor

- [x] 2.1 Add processor tests for the paginated GraphQL query: query variables, cursor continuation, no individual PR/status/check-run REST calls, Dependabot classification, missing authors, and `CLEAN`-only counting. (Files: `tests/unit/test_issues_processor.py`.)
- [x] 2.2 Add `_fetch_open_pull_request_metrics()` and its static GraphQL query to `IssuesRepoProcessor`; paginate, classify PRs, and write the four documented integer result keys. (Files: `src/ghbot/modes/issues.py`.)
- [x] 2.3 Add processor tests for recoverable GraphQL and malformed-payload failures, unavailable metrics, fetch-error events, partial status, and primary/secondary rate-limit propagation. (Files: `tests/unit/test_issues_processor.py`.)
- [x] 2.4 Implement the documented failure policy for bulk PR metrics, preserving `FatalError` propagation and making all four metrics unavailable after a recoverable failure. (Files: `src/ghbot/modes/issues.py`.)

## 3. Render pull-request metrics in every issues report style

- [x] 3.1 Add plain, table, and JSON report tests for per-repository and aggregate metrics, mixed available/unavailable repositories, and `N/A`/`null` output. (Files: `tests/unit/test_issues_report.py`.)
- [x] 3.2 Extend `IssuesCollectionReport` summaries, document records, plain repository blocks, and item-oriented table columns with the four documented metrics while preserving existing issue items and `--labels`. (Files: `src/ghbot/modes/issues.py`.)

## 4. Resolve accepted review feedback

- [x] 4.1 Classify GraphQL primary and secondary rate limits without broad message matching, and add regression coverage for structured and non-rate errors. (Files: `src/ghbot/github/client.py`, `tests/unit/test_client.py`.)
- [x] 4.2 Cover each malformed GraphQL response branch and assert table metric cells by position. (Files: `tests/unit/test_issues_processor.py`, `tests/unit/test_issues_report.py`.)
- [x] 4.3 Mark aggregate PR metrics unavailable when any repository is incomplete, and notify human and JSON consumers. (Files: `src/ghbot/modes/issues.py`, `tests/unit/test_issues_report.py`.)
