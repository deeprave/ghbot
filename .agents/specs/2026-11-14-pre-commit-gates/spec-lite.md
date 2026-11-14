# Pre-commit quality gates

## Problem

The repository has Python quality gates but does not run them automatically before commits.

## Goal

Add a versioned `.pre-commit-config.yaml`, add `pre-commit` to the uv development group, and install the Git hook in this checkout.

## Required hooks

- Standard hygiene: trailing whitespace, EOF fixing, YAML/TOML validation, merge-conflict detection, added-file size limits, and no direct commits to `main`.
- Project-wide gates with no filename arguments: `uv run ruff check`, `uv run ruff format --check`, `uv run ty check src/`, and `uv run pytest -Walways -Werror`.

## Constraints and success

No runtime dependencies or application behaviour changes. Install with `uv run pre-commit install`; verify the expected branch-guard rejection on `main` and run all remaining hooks with that guard skipped.
