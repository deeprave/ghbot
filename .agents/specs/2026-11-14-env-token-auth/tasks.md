# Implementation Tasks

- [x] 1. Add source-aware environment-token retrieval (`tests/unit/test_auth.py`, `src/ghbot/github/auth.py`)
  - [x] 1.1 Add failing tests for `GITHUB_API_TOKEN` retrieval, whitespace trimming, missing/empty failures without subprocess use, and source-isolated caches.
  - [x] 1.2 Implement concurrency-safe source-aware token retrieval while preserving default `gh auth token` behaviour.
- [x] 2. Wire explicit environment-token mode through the CLI (`tests/unit/test_main.py`, `src/ghbot/__main__.py`)
  - [x] 2.1 Add failing CLI and main-loop tests for global `-e` / `--env` selection and unflagged default authentication.
  - [x] 2.2 Add the global flag and pass its selected source to authentication without changing API-client construction.
- [x] 3. Document and verify (`README.md`, `.agents/steering/security.md`, `spec-lite.md`)
  - [x] 3.1 Document explicit `GITHUB_API_TOKEN` mode and update security steering without recording token values.
  - [x] 3.2 Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`; update tracking context.
- [x] 4. Add persistent environment-token selection and refresh documentation (`tests/unit/test_config.py`, `tests/unit/test_main.py`, `src/ghbot/config.py`, `src/ghbot/__main__.py`, `README.md`)
  - [x] 4.1 Add failing tests for `env = true` configuration selection, `--env` / `--no-env` overrides, and the default source.
  - [x] 4.2 Preserve `env = true` through CLI setup, with `--no-env` taking precedence, and use it for authentication source selection.
  - [x] 4.3 Correct the README authentication/configuration and architecture documentation, then rerun the Python gates.
