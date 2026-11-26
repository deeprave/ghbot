# Complexity estimate: combo reports

## T-shirt size

**L**

## Breakdown

- **New files:** approximately 1–2 for the combo coordinator and combined-report composition.
- **Modified files:** approximately 4–6: command wiring, shared scan orchestration, report-mode
  interfaces, report tests, and CLI tests.
- **Estimated tasks:** 9–11 test-first tasks.

## Key risks

- The command must discover each repository once while running three independent processors with
  the same discovery context, bounded concurrency, and existing fatal-rate-limit behaviour.
- Per-processor partial results must remain isolated, while human and JSON output preserves each
  standalone report's schema, formatting, ordering, and output-file behaviour.
- The existing spec predates the active report-style-handler refactor. Its earlier renderer-based
  language must be reconciled with that refactor's handler-owned collection reports rather than
  reintroducing duplicate formatting paths.

## Confidence

**High.** The processors, discovery record, TaskPool, and three standalone report contracts are
already established. The work is integration-heavy rather than dependent on an unknown API.

## Dependencies

- `report-style-handlers` — provides the collection-report composition boundary that combo uses.

## Recommendation

Run `design` after `report-style-handlers` has passed verification, so the design can target its
actual composition interface. Do not begin implementation until that dependency is settled.

## Similar past work

- `report-style-handlers` establishes the intended collection-report and style
  composition boundary.
- `release-drift` and `scan-issues` added standalone report modes whose
  output contracts must remain intact when nested by combo.
- `task-executor/memory.md` documents the existing TaskPool error and concurrency
  boundary that combo must preserve.
