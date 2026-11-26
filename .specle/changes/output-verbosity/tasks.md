# Implementation Plan: output-verbosity

## Overview

Four targeted changes to correct log-level assignments across `processor.py`, `log.py`,
`__main__.py`, and `github/client.py`. Each task follows TDD: write the failing test first
(Red), then the minimum implementation to pass it (Green), then refactor. All commands use
`uv run` (e.g. `uv run pytest`).

## Tasks

- [x] 1. Add `"debug"` to `LoggingMonitor.send_event` severity→level map
  - [x] 1.1 Write failing test for debug severity in `test_processor.py`
    - In `TestLoggingMonitor`, add `test_severity_debug_logs_at_debug`: send
      `FeedbackEvent(type="progress", severity="debug", message="…")` and assert
      `record.levelno == logging.DEBUG`
    - Run `uv run pytest tests/unit/test_processor.py -k test_severity_debug` — expect RED
    - _Requirements: 2.2, 5.1_

  - [x] 1.2 Implement: add `"debug"` entry to `level_map` in `LoggingMonitor.send_event`
    - In `processor.py`, add `"debug": self._log.debug` to the `level_map` dict
    - Run `uv run pytest tests/unit/test_processor.py` — expect GREEN
    - _Requirements: 2.2, 5.1_

  - [x] 1.3 Extend property test `test_severity_to_log_level` to include `"debug"`
    - **Property 2: Severity-to-log-level mapping is complete and correct**
    - **Validates: Requirements 2.2, 5.1, 5.2, 5.3, 5.4, 5.5**
    - In `test_processor_props.py`, add `"debug": logging.DEBUG` to `SEVERITY_TO_LEVEL` and
      change `st.sampled_from(["info", "warning", "error"])` to
      `st.sampled_from(["debug", "info", "warning", "error"])` in `test_severity_to_log_level`
    - Run `uv run pytest tests/unit/test_processor_props.py -k test_severity_to_log_level` — expect GREEN

- [x] 2. Change `InfoRepoProcessor` event severities
  - [x] 2.1 Write failing tests for the 8 fetch-step progress events in `test_info_processor.py`
    - Update `test_run_sends_per_step_progress_events`: change the assertion from
      `e.severity == "info"` to `e.severity == "debug"` for the 8 middle progress events
    - Run `uv run pytest tests/unit/test_info_processor.py -k test_run_sends_per_step` — expect RED
    - _Requirements: 2.1_

  - [x] 2.2 Implement: change all 8 fetch-step progress `FeedbackEvent` severities `"info"` → `"debug"`
    - In `processor.py`, in each of the 8 `_fetch_*` methods, change the opening
      `FeedbackEvent("progress", "info", "fetching …")` call to `"debug"`
    - Affected methods: `_fetch_repo_metadata`, `_fetch_file_count`, `_fetch_languages`,
      `_fetch_contributors`, `_fetch_latest_release`, `_fetch_open_pull_requests`,
      `_fetch_open_issues`, `_fetch_security_alerts`
    - Run `uv run pytest tests/unit/test_info_processor.py` — expect GREEN
    - _Requirements: 2.1_

  - [x] 2.3 Write failing tests for the 4 empty-state events in `test_info_processor.py`
    - Update `test_no_releases_sends_warning_event`: assert `e.severity == "debug"` (not `"warning"`)
    - Update `test_empty_languages_sends_warning_event`: assert `e.severity == "debug"`
    - Add `test_languages_not_found_sends_debug_event`: inject `GitHubNotFoundError` on the
      languages endpoint, assert the captured event has `severity == "debug"`
    - Update `test_security_alerts_403_sends_warning_event`: assert `e.severity == "debug"`
    - Run `uv run pytest tests/unit/test_info_processor.py -k "warning_event or debug_event"` — expect RED
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.4 Implement: change 4 empty-state `FeedbackEvent` severities `"warning"` → `"debug"`
    - In `_fetch_latest_release`: `GitHubNotFoundError` branch → `"debug"`
    - In `_fetch_languages`: empty-response branch → `"debug"`; `GitHubNotFoundError` branch → `"debug"`
    - In `_fetch_security_alerts`: `GitHubNotFoundError` branch → `"debug"`
    - Run `uv run pytest tests/unit/test_info_processor.py` — expect GREEN
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.5 Write failing test for the `run()` finish event severity in `test_info_processor.py`
    - Update `test_run_sends_finish_progress_event`: change `assert last.severity == "info"` to
      `assert last.severity == "debug"`
    - Run `uv run pytest tests/unit/test_info_processor.py -k test_run_sends_finish` — expect RED
    - _Requirements: 3.2_

  - [x] 2.6 Implement: change `run()` finish `FeedbackEvent` severity `"info"` → `"debug"`
    - In `processor.py`, in `run()`, change the final
      `FeedbackEvent("progress", "info", "processing finished")` to `"debug"`
    - Run `uv run pytest tests/unit/test_info_processor.py` — expect GREEN
    - _Requirements: 3.2_

  - [x] 2.7 Write property test for empty-state debug severity in `test_processor_props.py`
    - **Property 1: Empty-state conditions emit debug-severity events**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    - Add `test_empty_state_events_are_debug` using
      `st.sampled_from(["release_not_found", "languages_empty", "languages_not_found", "security_not_found"])`
    - For each variant, configure the gh mock to trigger that condition, run the processor,
      collect all `FeedbackEvent` objects passed to `monitor.send_event`, and assert the
      empty-state event has `severity == "debug"`
    - Patch at `ghbot.processor.github_api_call`
    - Run `uv run pytest tests/unit/test_processor_props.py -k test_empty_state` — expect GREEN

  - [x] 2.8 Write property test for run lifecycle event severities in `test_processor_props.py`
    - **Property 3: Run lifecycle events have correct severities**
    - **Validates: Requirements 3.1, 3.2**
    - Add `test_run_lifecycle_event_severities`: run the processor with all steps succeeding,
      collect all `send_event` calls, assert the first call has `type="progress"` and
      `severity="info"`, and the last call has `type="progress"` and `severity="debug"`
    - Patch at `ghbot.processor.github_api_call`; use `_make_succeeding_gh()` helper
    - Run `uv run pytest tests/unit/test_processor_props.py -k test_run_lifecycle` — expect GREEN

- [x] 3. Checkpoint — processor severity changes complete
  - Run `uv run pytest tests/unit/test_processor.py tests/unit/test_info_processor.py tests/unit/test_processor_props.py`
  - Ensure all tests pass; ask the user if questions arise.

- [x] 4. Add `requests: bool` parameter to `configure()` in `log.py`
  - [x] 4.1 Create `tests/unit/test_log.py` with failing tests for the new `requests` parameter
    - `test_configure_suppresses_requests_logger_by_default`: call `configure()` without
      `requests=True`, assert
      `logging.getLogger("ghbot.requests").level > logging.DEBUG`
    - `test_configure_enables_requests_logger_when_flag_set`: call `configure(requests=True)`,
      assert `logging.getLogger("ghbot.requests").level <= logging.DEBUG`
    - Add teardown to reset the logger after each test:
      `logging.getLogger("ghbot.requests").setLevel(logging.NOTSET)` and
      `logging.getLogger().handlers.clear()` to avoid cross-test pollution
    - Run `uv run pytest tests/unit/test_log.py` — expect RED (TypeError on unexpected kwarg)
    - _Requirements: 4.2, 4.3_

  - [x] 4.2 Implement: add `requests: bool = False` to `configure()` and silence the logger when `False`
    - Add `requests: bool = False` to the `configure()` signature in `log.py`
    - After the existing handler setup, add:
      ```python
      requests_logger = logging.getLogger("ghbot.requests")
      if not requests:
          requests_logger.setLevel(logging.CRITICAL + 1)
      ```
    - Run `uv run pytest tests/unit/test_log.py` — expect GREEN
    - _Requirements: 4.2, 4.3_

- [x] 5. Add `--requests` CLI flag to `main()` in `__main__.py`
  - [x] 5.1 Write failing tests for the `--requests` flag in `test_main.py`
    - `test_requests_flag_defaults_false`: invoke `main` without `--requests`, patch
      `ghbot.__main__.configure`, assert it was called with `requests=False`
    - `test_requests_flag_true`: invoke `main` with `--requests`, patch
      `ghbot.__main__.configure`, assert it was called with `requests=True`
    - Run `uv run pytest tests/unit/test_main.py -k requests_flag` — expect RED
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 5.2 Implement: add `--requests` flag to `main()` and thread it through to `configure()`
    - Add `@click.option("--requests", is_flag=True, default=False, help="Enable HTTP request/response detail logging (ghbot.requests logger)")` decorator to `main()`
    - Add `requests: bool` to the `main()` function signature
    - Add `requests=requests` to the `configure(...)` call
    - Run `uv run pytest tests/unit/test_main.py` — expect GREEN
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 6. Add entry/exit debug logging to `github_api_call` in `github/client.py`
  - [x] 6.1 Write failing tests for request logging in `test_client.py`
    - Add `test_github_api_call_logs_debug_on_entry`: use a `MemoryHandler` on
      `logging.getLogger("ghbot.requests")`, call `github_api_call` with a no-op body,
      assert at least one `DEBUG` record was emitted before the yield
    - Add `test_github_api_call_logs_debug_on_exit`: assert at least one `DEBUG` record was
      emitted after a successful yield (i.e. two records total for entry + exit)
    - Add `test_github_api_call_logs_use_requests_logger`: assert all debug records come from
      the `ghbot.requests` logger, not the general application logger
    - Run `uv run pytest tests/unit/test_client.py -k logs_debug` — expect RED
    - _Requirements: 4.4_

  - [x] 6.2 Implement: add module-level `_requests_log` and entry/exit debug calls in `client.py`
    - Add `from ghbot.log import get_logger` import to `client.py`
    - Add `_requests_log = get_logger("ghbot.requests")` at module level
    - In `github_api_call`, add `_requests_log.debug("github api call starting")` before `yield`
      and `_requests_log.debug("github api call completed")` after `yield` (inside the `try`)
    - Run `uv run pytest tests/unit/test_client.py` — expect GREEN
    - _Requirements: 4.4_

  - [x] 6.3 Write property test that `LoggingMonitor` never routes to the requests logger
    - **Property 4: LoggingMonitor never routes to the requests logger**
    - **Validates: Requirement 4.5**
    - Add `test_logging_monitor_never_uses_requests_logger` in `test_processor_props.py`:
      attach a `MemoryHandler` to `logging.getLogger("ghbot.requests")`, send an arbitrary
      `FeedbackEvent` through `LoggingMonitor.send_event`, assert the handler's buffer is empty
    - Use `st.builds(FeedbackEvent, type=st.text(), severity=st.text(), message=st.text())`
    - Run `uv run pytest tests/unit/test_processor_props.py -k test_logging_monitor_never` — expect GREEN

- [x] 7. Final checkpoint — all tests pass
  - Run `uv run pytest tests/unit/`
  - Ensure all tests pass; ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- TDD cycle: write the failing test first (Red), then minimum implementation (Green), then refactor
- Always use `uv run pytest` — never bare `pytest`
- Async tests use `@pytest.mark.anyio`; async mocks use `AsyncMock`
- Patch at the import site: `ghbot.processor.github_api_call`, `ghbot.__main__.configure`
- `configure()` tests must reset logger state in teardown to avoid cross-test pollution
- Property tests use `@settings(max_examples=100)` (Hypothesis)
- Each property test references its property number and the requirements it validates
