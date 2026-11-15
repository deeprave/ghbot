# Complexity estimate: report styles and mode handlers

## T-shirt size

**L**

## Breakdown

- **New files:** approximately 2–4 for the mode-handler, collection-report, and report-style
  boundaries; the design should choose the final module layout.
- **Modified files:** approximately 5–7: `report.py`, `__main__.py`, the three report test modules,
  command tests, and potentially public command documentation.
- **Estimated tasks:** 9–12 implementation tasks, including contract-regression tests before
  removal of legacy render paths.

## Key risks

- The public contract spans security, issues, and drift in plain, Markdown-table, and JSON output.
  Issues adds a labels variant. Summaries, filtering, sort order, unavailable values, output files,
  and format-conflict errors must remain unchanged.
- The existing execution model collects `RepoResult` values from `TaskPool` and then selects a
  top-level render function. The design must make handlers collection-aware without changing
  processor execution, API calls, concurrency, or rate-limit behaviour.
- The new interfaces must preserve deterministic output despite concurrent scans and allow the
  later `combo` command to embed existing JSON documents and render ordered human-readable
  sections without format-specific duplication.
- `2026-11-14-combo-reports` currently describes reusing report renderers. Its design must be
  reconciled with this handler-based architecture once this refactor establishes the shared
  composition boundary.

## Confidence

**High.** The report and command boundaries are contained, and existing focused tests define the
compatibility surface. The difficulty is preserving that surface through an architectural split,
not uncertainty about external systems.

## Recommendation

Run the `design` skill before task breakdown. It should establish the handler/style interfaces,
the collection aggregation flow, direct mode-module migration, and the composition contract for
`combo`.

## Similar past work

- `2026-11-08-release-drift` added a third report implementation and its plain/table/JSON contract
  to the shared `report.py` module.
- `2026-07-29-scan-issues` added the report mode with the most specialised presentation behaviour,
  including item rows and optional labels.
- No directly relevant `memory.md` artifact exists for prior report refactors.
