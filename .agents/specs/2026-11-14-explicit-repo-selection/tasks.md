# Implementation Tasks

- [x] 1. Resolve global explicit-selection inputs (`src/ghbot/__main__.py`, `tests/unit/test_main.py`)
  - [x] 1.1 Add failing shell tests for repeated and comma-separated `--repo`, repeated-`--repos` rejection, qualified-only input, bare expansion through CLI and TOML owners, bare-without-owner and malformed-entry usage errors, inline-before-file order, comment/empty/comma-separated file input, unreadable files, and case-insensitive duplicate warnings.
  - [x] 1.2 Add global `--repo` and single-use `--repos` options plus private shell helpers that parse entries, expand bare values, and store `None` or an insertion-ordered tuple of explicit `(owner, repo)` candidates in merged configuration.

- [x] 2. Validate explicit candidates through shared discovery (`src/ghbot/github/repos.py`, `tests/unit/test_repos.py`)
  - [x] 2.1 Add failing async tests for explicit validation URL variables, metadata-derived owner type, no owner lookup/listing, missing/access-denied skipping, retry-once behavior, rate-limit propagation, unknown owner type, archive filtering, and an empty explicit tuple that yields nothing.
  - [x] 2.2 Add the optional explicit-candidate scanner path using `github_api_call()` and `url_vars`; preserve owner-list scanning unchanged when selection is `None`.

- [x] 3. Carry selection through both runners (`src/ghbot/runner.py`, `tests/unit/test_runner.py`)
  - [x] 3.1 Add failing tests that `run_processor()` and `run_mode()` forward configured explicit candidates unchanged, while absent selection retains owner-based discovery arguments.
  - [x] 3.2 Forward `cfg["explicit_repositories"]` to the scanner from each runner without altering authentication, concurrency, processor construction, collection timing, or report output.
