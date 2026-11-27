# Estimate: Clean up dead code

## T-shirt size

S

## Breakdown

- New files: 0
- Modified files: approximately 8–10, including the Vulture whitelist, affected source modules,
  and tests that assert only removed implementation details.
- Estimated tasks: 4
- Key risks: mistaking a discovery or runtime protocol surface for unused code; weakening the
  Vulture gate through an over-broad suppression.

## Confidence

High. The hook identifies a finite set of candidates, and repository-wide reference evidence
already separates framework/protocol surfaces from the likely unused state.

## Recommendation

Proceed as one small change. Design must document each retained versus removed candidate before
implementation; no split is warranted because the candidates share the same validation gate.

## Similar past work

The recently defined Vulture pre-commit maintenance work established the hook and its intentional
framework/protocol whitelist. This change owns only the remaining production findings.
