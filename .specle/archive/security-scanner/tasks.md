# Implementation Plan: security-scanner

## Overview

Three areas of change: add `SecurityRepoProcessor` to `processor.py`, add `report.py` with
`print_security_report()`, and refactor `__main__.py` to a Click group with `info` and
`security` subcommands. Each task follows TDD: write the failing test first (Red), then
minimum implementation (Green). All commands use `uv run pytest`.

## Tasks

- [x] 1. Add `SecurityRepoProcessor` to `processor.py`
  - [x] 1.1 Write failing tests in `tests/unit/test_security_processor.py`
    - Constructor: empty owner raises `ValueError`, empty repo raises `ValueError`
    - `isinstance(processor, RepoProcessor)` passes
    - Happy path: all three endpoints return items → counts stored, status `"success"`
    - 403/404 on each endpoint → `None` count, debug event emitted, no error, status `"success"`
    - `GitHubApiError` on one endpoint → `None` count, error recorded, status `"partial"`
    - `FatalError` subclasses (`GitHubPrimaryRateLimitError`, `GitHubSecondaryRateLimitError`) re-raised from `run()`
    - Unexpected exception → status `"failed"`, error recorded, result returned
    - Run `uv run pytest tests/unit/test_security_processor.py` — expect RED (ImportError)
    - _Requirements: 3, 4, 5, 9_

  - [x] 1.2 Implement `SecurityRepoProcessor` in `processor.py`
    - Add class with constructor validation, `owner`/`repo` properties
    - Implement `run()` with same skeleton as `InfoRepoProcessor`: start event, three `_fetch_*` calls, `FatalError` re-raise, unexpected-exception catch, finish event
    - Implement `_fetch_dependabot_alerts`, `_fetch_code_scanning_alerts`, `_fetch_secret_scanning_alerts` — each uses `getiter` with `?state=open` in URL, counts items, handles `GitHubNotFoundError` → `None` + debug, `GitHubApiError` → `None` + error
    - Run `uv run pytest tests/unit/test_security_processor.py` — expect GREEN
    - _Requirements: 3, 4, 5, 9_

- [x] 2. Add `report.py` with `print_security_report()`
  - [x] 2.1 Write failing tests in `tests/unit/test_report.py`
    - All repos have alerts → correct totals printed, per-repo section present
    - No repos have issues → per-repo section absent
    - All repos returned `None` for a type → that type shows `"N/A"`
    - Mix of `None` and int counts → `None` excluded from sum
    - Empty results list → `"Repos scanned: 0"`, no per-repo section
    - Output captured via `capsys` — assert on stdout, nothing on stderr
    - Run `uv run pytest tests/unit/test_report.py` — expect RED (ImportError)
    - _Requirements: 6, 7, 8_

  - [x] 2.2 Implement `print_security_report()` in `src/ghbot/report.py`
    - Summary section: scanned, repos with issues, totals per alert type (`N/A` if all `None`)
    - Per-repo section: blank line separator, sorted by `owner/repo`, only repos with at least one non-None non-zero count
    - All output via `print()` (stdout); no logging calls
    - Run `uv run pytest tests/unit/test_report.py` — expect GREEN
    - _Requirements: 6, 7, 8_

- [x] 3. Checkpoint — processor and report tests pass
  - Run `uv run pytest tests/unit/test_security_processor.py tests/unit/test_report.py`
  - Ensure all pass before touching `__main__.py`

- [x] 4. Refactor `__main__.py` to Click group
  - [x] 4.1 Write failing tests in `tests/unit/test_main.py`
    - `ghbot` with no subcommand → exit code non-zero
    - `ghbot info` → `_main` called with `InfoRepoProcessor`
    - `ghbot security` → `_main` called with `SecurityRepoProcessor`
    - `ghbot security` → `print_security_report` called with `pool.results`
    - `ghbot info` → `print_security_report` not called
    - Global options (`--owner`, `--concurrency`, `--verbose`, `--requests`, etc.) still work with both subcommands
    - Run `uv run pytest tests/unit/test_main.py -k "subcommand or security or no_subcommand"` — expect RED
    - _Requirements: 1, 2, 3_

  - [x] 4.2 Refactor `__main__.py`
    - Rename `main` → `cli`, change decorator to `@click.group()`
    - Move all existing options and config-merge logic into `cli()`; store result in `ctx.obj["cfg"]`
    - Add `info` subcommand: calls `asyncio.run(_main(ctx.obj["cfg"], InfoRepoProcessor))`, handles `FatalError`
    - Add `security` subcommand: calls `asyncio.run(_main(ctx.obj["cfg"], SecurityRepoProcessor))`, handles `FatalError`, then calls `print_security_report(results)`
    - Update `_main(cfg, processor_cls)`: add `processor_cls` param, use it in the loop, return `pool.results`
    - Update imports: add `SecurityRepoProcessor` from `ghbot.processor`, add `print_security_report` from `ghbot.report`
    - Update `if __name__ == "__main__"` to call `cli()`
    - Run `uv run pytest tests/unit/test_main.py` — expect GREEN
    - _Requirements: 1, 2, 3_

- [x] 5. Final checkpoint — all tests pass
  - Run `uv run pytest tests/unit/`
  - Ensure all tests pass

## Notes

- `RecordingMonitor` stub pattern: same as `test_info_processor.py` — a simple class collecting events in a list
- Patch at import site: `ghbot.processor.github_api_call` for processor tests, `ghbot.__main__._main` for CLI routing tests
- `capsys` for report output assertions — assert `out` contains expected strings, `err` is empty
- Async tests use `@pytest.mark.anyio`; async mocks use `AsyncMock`
- The `security` subcommand calls `print_security_report` in the sync layer after `asyncio.run` returns, not inside `_main`
