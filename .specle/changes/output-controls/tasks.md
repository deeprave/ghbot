# Implementation Plan: output-controls

## Overview

Implement final-output controls in small TDD slices. Keep the current uncommitted behavior changes
under this spec:

- Security progress logging only reveals repositories that report issues.
- `found issues N` replaces `processing started` for issue-bearing security repositories.
- Compact table output is available as the `"table"` format.

## Tasks

- [x] 1. Add generic processor options plumbing
  - [x] 1.1 Update `RepoProcessor` constructor expectations in tests to include optional
    `options: dict | None = None`.
  - [x] 1.2 Update `_main` tests to assert the options dictionary is passed to processor
    constructors.
  - [x] 1.3 Implement `_main(cfg, processor_cls, options=None)` and pass `options=options` to
    constructed processors.
  - [x] 1.4 Update `InfoRepoProcessor` and `SecurityRepoProcessor` constructors to accept and store
    `dict(options or {})` while preserving existing call sites.

- [x] 2. Add security format CLI options
  - [x] 2.1 Add tests for default `"plain"` format and for `--plain`, `--table`, and `--json`.
  - [x] 2.2 Add tests that multiple format flags produce a Click usage error before processing.
  - [x] 2.3 Implement security-only format flags and helper to build `{"format": selected}`.
  - [x] 2.4 Add regression test that `info` does not accept `--json`, `--table`, or `--plain`.

- [x] 3. Refactor report rendering API
  - [x] 3.1 Add `render_security_report(results, *, format="plain") -> str` tests.
  - [x] 3.2 Preserve the previous stacked per-repository format as `"plain"`.
  - [x] 3.3 Move the compact Markdown table to `"table"`.
  - [x] 3.4 Keep `print_security_report(results)` backwards compatible by defaulting to plain.

- [x] 4. Add JSON report output
  - [x] 4.1 Add tests that JSON output parses as valid JSON.
  - [x] 4.2 Assert JSON has top-level `"summary"` and `"repositories"` keys.
  - [x] 4.3 Assert `"repositories"` contains one object per scanned repository, including clean
    repositories.
  - [x] 4.4 Assert JSON preserves unavailable counts as `null`.
  - [x] 4.5 Implement JSON rendering with stable key names.

- [x] 5. Add final report `--output` destination
  - [x] 5.1 Add CLI/report tests that stdout receives the final report when `--output` is omitted.
  - [x] 5.2 Add tests that `--output path` writes the final report to that file and leaves stdout
    empty for the final report.
  - [x] 5.3 Add tests that progress logs are not written into the output file.
  - [x] 5.4 Implement UTF-8 file writing and clear failures for unwritable paths.

- [x] 6. Adopt current uncommitted output changes into this spec
  - [x] 6.1 Keep security processor behavior: only issue-bearing repositories emit
    repository-specific progress and `found issues N`.
  - [x] 6.2 Keep compact fixed-width Markdown table implementation as the `"table"` renderer.
  - [x] 6.3 Update tests so the default report expectations move back to `"plain"` and table tests
    call/request `"table"`.

- [x] 7. Final verification
  - [x] 7.1 Run `uv run pytest -v -Werror -Walways`.
  - [x] 7.2 Run `uv run ruff check`.
  - [x] 7.3 Run `uv run ty check src/`.
  - [x] 7.4 Run `uv run ruff format --check`.
