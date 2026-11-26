# Implementation Tasks

- [x] 1. Implement the dispatch-only release workflow (`.github/workflows/python-release-publish.yml`)
  - [x] 1.1 Replace the release event trigger with a main-only dispatch and exact-SHA `Validate` gate.
  - [x] 1.2 Read the version from `pyproject.toml`, publish through OIDC, then create the matching GitHub Release with narrow job permissions.
- [x] 2. Verify and record completion
  - [x] 2.1 Update the compact spec with implementation outcome.
  - [x] 2.2 Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
