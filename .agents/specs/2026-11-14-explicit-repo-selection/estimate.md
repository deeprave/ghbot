# Complexity estimate: explicit repository selection

## T-shirt size

**L**

## Breakdown

- **New files:** approximately 1–2 for ordered selection parsing and explicit-repository scanner
  helpers.
- **Modified files:** approximately 4–6: Click command setup, configuration handoff, repository
  discovery, scanner tests, CLI tests, and documentation.
- **Estimated tasks:** 10–12 test-first tasks.

## Key risks

- Click's ordinary `multiple=True` option values do not by themselves retain the relative order of
  interleaved `--owner`, `--repo`, and `--repos` occurrences. The implementation needs a clear,
  testable ordered-input boundary rather than post-processing grouped option values.
- Explicit mode must bypass owner listing completely while retaining the shared
  `DiscoveredRepository` record, owner type, archive filtering, retry-and-skip policy, and
  rate-limit propagation.
- File parsing must preserve context at the position of each `--repos` occurrence, ignore only the
  specified comments and empty entries, and surface file failures as actionable usage errors.

## Confidence

**Medium.** The scanner's validation and error policy are well established, but the precise Click
integration needed to retain global-option order is the main implementation risk.

## Recommendation

Run `design` before tasks. It should select the ordered-argument capture mechanism and define the
selection representation and scanner interface before implementation begins.

## Similar past work

- `2026-03-06-scan-repositories/memory.md` documents configuration merging, Click owner parsing,
  scanner retry behaviour, and import-site testing conventions.
- `2026-11-13-org-private-discovery` established `DiscoveredRepository`, owner-type propagation,
  archive filtering, and the scanner's retry/rate-limit policies.
