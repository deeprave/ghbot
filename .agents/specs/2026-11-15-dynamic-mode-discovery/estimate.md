# Complexity estimate: dynamic mode discovery

## T-shirt size

**M**

## Breakdown

- **New files:** approximately 2–3: a discovery module, an `info` mode module, and focused
  discovery/integration tests.
- **Modified files:** approximately 5–6: `src/ghbot/modes/__init__.py`,
  `src/ghbot/__main__.py`, the existing reportable mode definitions, and CLI integration tests.
- **Estimated tasks:** 5–7 test-first tasks.

## Key risks

- Package discovery must load strictly from installed `ghbot.modes` and provide actionable startup errors on duplicate canonical names or malformed definitions, preventing arbitrary filesystem or third-party loading.
- Dynamic Click command registration must preserve existing command names, options, help text,
  output-file behaviour, and error handling for `security`, `issues`, `drift`, and `info`.
- The `info` migration must retain its non-reporting runner path while making it a discoverable
  unit.
- The discovery protocol must be sufficient for the separately planned combo implementation
  without prematurely adding its selection, execution, or rendering mechanics.

## Confidence

**High.** `mode-cli-ownership` already separated mode-owned Click commands and the neutral async
runner. `report-style-handlers` already gives reportable modes their collections. The remaining
work is a bounded registration and metadata refactor.

## Dependencies

- `report-style-handlers` — completed; supplies mode-owned report collection interfaces.
- `mode-cli-ownership` — completed; supplies mode-owned Click command architecture and extracted scan runner.
- `combo-reports` — remains a separate queued change that will consume combinable discovery
  metadata.

## Recommendation

Run `design` before creating implementation tasks to define the discovery protocol, package
validation, command registration, and the non-reporting info-mode boundary.

## Similar past work

- `2026-11-15-mode-cli-ownership` established decentralized mode commands and the neutral async runner.
- `2026-11-14-report-style-handlers` established mode collections, report styles, and section composition.
