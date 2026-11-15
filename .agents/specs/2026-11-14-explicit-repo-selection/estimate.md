# Complexity estimate: explicit repository selection

## T-shirt size

**L**

## Breakdown

- **New files:** approximately 1–2 for ordered selection parsing and explicit-repository discovery helpers.
- **Modified files:** approximately 4–6: global Click configuration, shared runner handoff, repository discovery, scanner tests, CLI tests, and documentation. Mode modules are not expected to change.
- **Estimated tasks:** 10–12 test-first tasks.

## Key risks

- Bare entries must expand deterministically across the flattened `--owner` list, while qualified
  and expanded candidates are normalized with a case-folded key, logged, and deduplicated before validation.
- Explicit mode must bypass owner listing completely through the discovery path shared by `run_processor()` and `run_mode()`, while retaining the shared `DiscoveredRepository` record, owner type, archive filtering, retry-and-skip policy, and rate-limit propagation.
- File parsing must retain entry order, ignore only the specified comments and empty entries, and surface file failures as actionable usage errors.

## Confidence

**High.** The scanner's validation and error policy are well established, and the existing flattened
owner list removes the need for custom Click argument-order capture.

## Recommendation

Run `design` before tasks. It should select the ordered-argument capture mechanism and define the
selection representation and scanner interface before implementation begins.

## Similar past work

- `2026-03-06-scan-repositories/memory.md` documents configuration merging, Click owner parsing,
  scanner retry behaviour, and import-site testing conventions.
- `2026-11-13-org-private-discovery` established `DiscoveredRepository`, owner-type propagation,
  archive filtering, and the scanner's retry/rate-limit policies.
