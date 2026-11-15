# Complexity estimate: issues CI report

## T-shirt size

**M**

## Breakdown

- **New files:** none expected; the change extends the issues processor and its report mode.
- **Modified files:** approximately 4–5: issues processor, report-mode/rendering code, processor
  tests, report tests, and command tests where result handoff changes.
- **Estimated tasks:** 7–9 test-first tasks.

## Key risks

- The repository already has combined-status and check-run helpers in the security processor, but
  its “ready” decision also rejects drafts and known merge conflicts. This feature must reuse only
  the CI-success criteria, not those non-CI conditions.
- Each open pull request may require two API lookups. The implementation must preserve partial
  result policy by excluding only a failed pull request from CI-passing counts while retaining the
  category totals and propagating rate limits.
- Four new metrics must preserve the issues report's `N/A`/`null` semantics across plain, table,
  and JSON output. The active report-style-handler refactor may relocate the relevant mode code.

## Confidence

**High.** The endpoint templates, wrapper, error policy, and check-run criteria already exist in
the security processor. The main work is extracting the correct CI-only predicate and extending
the established issues-report contract.

## Dependencies

- `report-style-handlers` — determines the issues mode-module and report-style integration point.

## Recommendation

Run `design` after `report-style-handlers` is verified. It should define the shared CI-only helper
and issues result keys in the refactored mode-module layout; splitting the implementation is not
otherwise necessary.

## Similar past work

- `2026-05-06-enhance-security-info` introduced combined-status and check-run evaluation for
  Dependabot PRs, including failure, pending, unavailable, and rate-limit coverage.
- `2026-07-29-scan-issues` established the issues processor's record shape and plain/table/JSON
  rendering contract.
