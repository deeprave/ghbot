# Clean up dead code

## Problem

The newly added Vulture pre-commit hook reports unused production symbols and stored state. Some
are known framework or protocol surfaces and are intentionally whitelisted; the remaining reports
need a source-level assessment before they can be removed safely.

## Outcome

Remove production code that is demonstrably unused, while preserving supported, reflective, and
runtime protocol contracts. The Vulture hook will pass at its normal 60% confidence threshold
without broad suppression of confirmed dead code.

## Scope

- Assess and, where confirmed, remove `UnexpectedError`, unused processor option snapshots,
  unused mode `processor_type` fields, and the unused client attribute set by the runner.
- Remove or update tests that exist only for code removed by this change.
- Keep narrow Vulture whitelist/configuration entries for actual framework and protocol surfaces.

## Boundaries

- No feature behaviour, CLI contract, GitHub API behaviour, or report output changes.
- Do not remove an item merely because static analysis cannot observe dynamic use.
- Do not widen Vulture exclusions or raise its confidence threshold to conceal a finding.

## Verification

Run the focused and full project quality gates, then demonstrate that `uv run pre-commit run
vulture --all-files` passes at the configured threshold.
