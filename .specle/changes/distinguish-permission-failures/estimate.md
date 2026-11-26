# Estimate: distinguish permission failures

## T-shirt size

**L**

## Breakdown

- **New files:** ~0 production files; likely no new test modules.
- **Modified files:** ~14–18 across GitHub error translation and discovery, shared result/report
  representation, security/issues/drift processors and renderers, current schemas, README, and
  focused unit tests.
- **Estimated tasks:** ~7–9 implementation tasks after design.

## Key risks

- GitHub intentionally uses 404 to conceal private resources, so the implementation must preserve
  that documented ambiguity instead of manufacturing a permission conclusion.
- Disabled-feature response semantics vary by endpoint; the design must identify the supported
  signals and preserve ordinary API-error handling when a response is not classifiable.
- Explicit repository failures must become report results without changing owner discovery or
  duplicating repositories across standalone and combined reports.
- Exit status 8 must be emitted only after report output is written and only for unavailable
  explicitly selected repositories; per-metric availability remains non-fatal.
- The `unavailable` contract touches every report schema and existing human-rendering expectations.

## Confidence

**Medium.** The target behaviour is clear, but endpoint-specific disabled-feature classification
and the existing collection/result boundary need design investigation.

## Recommendation

Proceed with **design**. This should remain one change because exception taxonomy, result
representation, schema evolution, rendering, and exit status form one consumer-visible contract.

## Similar past work

- `versioned-report-schemas`: packaged `1.0` schema contract evolution without a
  release-version bump.
- `rate-limit-resilience`: explicit repository ledgers, incomplete report outcomes,
  distinct post-output exit handling, and cross-mode propagation.
