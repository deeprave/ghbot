# Ruff 0.16 lint remediation

## Defect

After `uv sync --upgrade` updated Ruff to 0.16.1, the repository fails
`uv run ruff check`. Ruff's newer rules report remaining issues in production
code and tests.

## Reproduction

Run `uv run ruff check` after the dependency upgrade.

## Expected and actual

Expected: the existing source and tests pass linting without changing runtime
behaviour.

Actual: Ruff reports unused test variables, nested context managers, broad
exception catches, and modern type/timezone guidance.

## Root cause

The project allowed any Ruff version at or above 0.15.5. Ruff 0.16.1 enables
additional rules against code that was previously accepted.

## Fix approach

Apply behaviour-preserving source and test cleanups. Keep the intentional
catch-all error handling and document it inline for Ruff, rather than changing
the TaskPool and processor error policy. Use UTC for structured log timestamps.
Scope CI's Ruff checks to `src` and `tests`, so repository documentation is not
treated as executable code formatting input.
