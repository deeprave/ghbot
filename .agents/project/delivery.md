# Delivery policy

## Model and authority

- Use Specle's shared-upstream branch-and-pull-request delivery model.
- The delivery branch is `main`.
- Create branches and pull requests only when explicitly authorised by the user. Merge only on explicit user instruction.
- After an explicitly directed merge, synchronise the local checkout to `main`.

## Branches and commits

- Normal `kind: "change"` records use `feature/<slug>`. Bugfixes use `bugfix/<slug>`, refactors use `refactor/<slug>`, and maintenance work uses `chore/<slug>`.
- Use Conventional Commit-style titles, for example `feat: add security severity breakdowns`.

## Required checks

- Before a pull request is ready to merge, run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
- Configured GitHub security checks, including CodeQL and GitGuardian, must pass when applicable. A documented GitHub service failure is an external blocker, not a source-code failure.

## Pull requests

- Use concise `Summary`, `Changes`, `Impact`, and `Notes` sections.
- Explain the change; do not include test, coverage, or similar statistics.
- Include `Closes #<number>` when the pull request implements a GitHub issue.
