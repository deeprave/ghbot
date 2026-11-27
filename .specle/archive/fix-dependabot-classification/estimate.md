# Estimate: Fix Dependabot classification

## T-shirt size

S

## Breakdown

- New files: 0.
- Modified files: approximately 3–4: a shared classification helper, the issues and security modes, and their unit tests.
- Estimated tasks: 3.
- Key risks: GitHub's REST and GraphQL login forms must be recognised exactly without broadening classification to unrelated accounts; both modes must retain their existing result and output contracts.

## Confidence

High. The inconsistent literal comparisons and their reporting effects are directly evidenced in the processors and unit-test fixtures.

## Recommendation

Keep this as one bounded normal change. Centralise the recognised login set in the existing shared processor layer, update both callers, and add focused regression coverage for GraphQL's `dependabot` form alongside the bot-suffixed form.

## Similar past work

`security-add-severity` established the current security reporting conventions; this change preserves those report contracts while correcting shared pull-request identity classification.
