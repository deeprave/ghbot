# Implementation Tasks: distinguish permission failures

- [x] 1. Classify non-rate-limit permission failures at the GitHub boundary (`tests/unit/test_github_client.py`, `src/ghbot/errors.py`, `src/ghbot/github/client.py`)
  - [x] 1.1 Add failing client tests that distinguish REST and GraphQL 404, ordinary 403/`FORBIDDEN`, primary and secondary rate-limit responses, and verify safe exception messages.
  - [x] 1.2 Add `GitHubForbiddenError` and raise it only for REST or GraphQL 403 responses that are not rate limits, preserving the current 404 and rate-limit paths.

- [x] 2. Preserve unavailable metric causes in processor results (`tests/unit/test_*_processor.py`, `src/ghbot/processor.py`, `src/ghbot/modes/*.py`)
  - [x] 2.1 Repair collected processor tests and add coverage for forbidden, not-found, documented disabled-feature, and ordinary recoverable API responses, including nullable-value compatibility and safe messages.
  - [x] 2.2 Add the typed per-metric availability mapping to `RepoResult`, then map each supported endpoint failure to `not_found`, `forbidden`, `disabled`, or `error` without changing rate-limit propagation; disabled security features alone do not make a result partial.

- [x] 3. Retain explicit unavailable repository selections (`tests/unit/test_github_repos.py`, `tests/unit/test_*_report_mode.py`, `src/ghbot/github/repos.py`, `src/ghbot/modes/*.py`)
  - [x] 3.1 Add failing tests that an explicitly selected missing or forbidden repository produces a failed result, an archived selection produces a skipped result, and owner discovery retains its existing omission behaviour.
  - [x] 3.2 Add explicit-selection outcomes and runner conversion to report-visible results without constructing a processor or issuing metric requests; log only the repository identifier and classified reason.

- [x] 4. Expose availability and explicit-selection outcomes in every report form (`tests/unit/test_*_report.py`, `src/ghbot/modes/*.py`, `src/ghbot/schema_resources/*.json`)
  - [x] 4.1 Add failing JSON, plain, table, and schema tests for optional `unavailable` entries, allowed reasons, invalid-reason rejection, explicit failed/skipped results, aligned `N/A (<reason>)` rendering, table status/reason visibility, and metric-level drift unavailability.
  - [x] 4.2 Serialize the availability mapping, retain explicit outcomes and metric-level drift failures through collection filters, add shared reason-marker rendering, exclude unavailable outcomes from active summaries, and extend each current `1.0` schema without changing its identifier.

- [x] 5. Return the post-output unavailable-repository exit status and document the contract (`tests/unit/test_*_report_mode.py`, `src/ghbot/modes/*.py`, `README.md`)
  - [x] 5.1 Add failing command tests that reports are written before exit 8 for unavailable explicit selections, metric-only unavailability exits 0, and a rate-limit abort retains precedence with exit 4.
  - [x] 5.2 Carry explicit-repository availability through `ReportOutcome`, write and log the completed report before returning exit 8, and document the taxonomy, ambiguous 404s, reason markers, and why exit 8 signals missing expected data.

- [x] 6. Run focused regression coverage and the required quality gates (`tests/unit/`, `src/`)
  - [x] 6.1 Run the focused client, discovery, processor, report, schema, and command tests after each preceding slice.
  - [x] 6.2 Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
