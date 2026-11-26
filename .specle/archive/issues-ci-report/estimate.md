# Complexity estimate: issues merge-ready report

## T-shirt size

**M**

## Breakdown

- **New files:** none expected.
- **Modified files:** approximately 3–4: `src/ghbot/modes/issues.py`, GraphQL client support only if the existing client cannot issue the required query, and focused issues processor/report tests.
- **Estimated tasks:** 5–7 test-first implementation tasks.

## Key risks

- The completed report-style and mode-ownership refactors place both the issues processor and its collection/report in `src/ghbot/modes/issues.py`; implementation should extend that unit rather than revive a central reporting path.
- The bulk GraphQL query needs pagination for all open pull requests without falling back to individual pull-request REST requests.
- The design must preserve the project’s existing GitHub API error and rate-limit policy when adapting or introducing the GraphQL client call.
- `mergeStateStatus` must use GitHub’s exact `CLEAN` value: all other states, including `HAS_HOOKS`, do not count as merge-ready.
- The four metrics must preserve established `N/A`/`null` semantics in plain, table, and JSON
  reports.

## Confidence

**Medium-high.** GitHub’s GraphQL schema exposes the required pull-request author and merge-state fields in a paginated connection. The remaining uncertainty is contained to the repository’s existing GraphQL-client surface and its error translation.

## Dependencies

- `report-style-handlers` — complete; its mode-local layout is now the implementation target.
- `mode-cli-ownership` — complete; the issues command already delegates through `run_mode()`.

## Recommendation

Run `design` next. It should specify the GraphQL query and pagination contract, `CLEAN`-only classification, result keys, bulk-query failure behaviour, and the output schema before tasks are written.

## Similar past work

- `enhance-security-info` established GitHub API error and rate-limit handling for pull-request reporting.
- `scan-issues` established the issues processor's item record shape and
  plain/table/JSON reporting contract.
