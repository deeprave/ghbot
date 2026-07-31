# Tasks

- [x] Reproduce the Ruff 0.16.1 lint failures with `uv run ruff check`.
- [x] Add or update tests for any observable behaviour change.
- [x] Apply manual fixes for the remaining lint findings.
- [x] Run pytest, Ruff, ty, and source/test formatting verification.
- [x] Scope CI Ruff formatting and linting to source and tests.

## Verification note

CI now runs Ruff only against `src` and `tests`, so historical Markdown code
blocks are intentionally outside its scope.
