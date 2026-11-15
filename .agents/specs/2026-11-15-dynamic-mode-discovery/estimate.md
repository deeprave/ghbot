# Complexity estimate: dynamic mode discovery

## T-shirt size

**L**

## Breakdown

- **New files:** approximately 2–3 (`src/ghbot/modes/discovery.py`, `src/ghbot/modes/combo.py`, and test modules `tests/unit/test_discovery.py`, `tests/unit/test_combo.py`).
- **Modified files:** approximately 5–7: `src/ghbot/modes/__init__.py`, `src/ghbot/__main__.py`, `src/ghbot/runner.py`, mode definitions in `security.py`, `issues.py`, `drift.py`, `processor.py` (info mode), and CLI integration tests.
- **Estimated tasks:** 8–11 test-first tasks.

## Key risks

- Package discovery must load strictly from installed `ghbot.modes` and provide actionable startup errors on duplicate canonical names or malformed definitions, preventing arbitrary filesystem or third-party loading.
- Dynamic Click command registration must seamlessly preserve all existing command names, options, help text, output file behavior, and error handling for standalone modes (`security`, `issues`, `drift`) as well as `info`.
- Multi-mode scanning in `combo` must discover repositories once, fan out to selected mode processors concurrently under bounded `TaskPool` limits, isolate partial failures per processor, and propagate fatal rate-limit errors cleanly.
- Mode option parsing, combo selection/exclusion flags, and deterministic ordering across plain, table, and JSON formats require well-defined interfaces.

## Confidence

**High.** The underlying abstractions are mature: `report-style-handlers` established `CombinedCollectionReport` and collection protocols, while `mode-cli-ownership` separated the scan runner and decentralized Click command definitions.

## Dependencies

- `report-style-handlers` — completed; supplies `CombinedCollectionReport` and collection rendering interfaces.
- `mode-cli-ownership` — completed; supplies mode-owned Click command architecture and extracted scan runner.

## Recommendation

Run `design` before creating implementation tasks to define the mode protocol, discovery validation rules, combo execution coordination, and CLI option routing.

## Similar past work

- `2026-11-15-mode-cli-ownership` established decentralized mode commands and the neutral async runner.
- `2026-11-14-report-style-handlers` established mode collections, report styles, and section composition.
- `2026-11-14-combo-reports` defined the composite report requirements and multi-processor execution scope.
