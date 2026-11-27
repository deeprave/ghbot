# Refactor CLI command surface

## Problem

The `schema` subcommand does not scan repositories or run processors, unlike every other top-level
command. CLI help also describes equivalent scan commands with inconsistent verbs and sentence
forms.

## Outcome

Expose installed schemas through a leading `--schema` invocation and make every processor-backed
command read `Scan for …` in help output.

## Scope

- Replace `ghbot schema …` with the leading forms `ghbot --schema REPORT`,
  `ghbot --schema --id TEXT`, and `ghbot --schema --list`.
- Dispatch a leading schema invocation before normal command selection so schema-only selectors
  remain invalid outside it.
- Standardise scan-command help descriptions for combo, info, drift, issues, and security.
- Update CLI documentation and focused command tests.

## Boundaries

- Schema contents and Python-level schema APIs remain unchanged.
- `--schema` must be the first user-supplied argument; this is the explicit dispatch boundary.
- No repository processors run during schema retrieval.

## Verification

Tests will cover every supported schema form, rejection of the removed command and ungated schema
selectors, absence of processor execution, and the consistent help descriptions. Existing schema
registry and package-distribution tests continue to cover resource availability.
