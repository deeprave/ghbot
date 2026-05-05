# Implementation Plan: repo-processor

## Overview

Implement a protocol-based repository-processing architecture in `src/ghbot/processor.py`. Build data types first (`ProcessingStatus`, `FeedbackEvent`, `RepoResult`), then protocols (`Monitor`, `RepoProcessor`), then concrete implementations (`LoggingMonitor`, `InfoRepoProcessor`), and finally wire into `_main`. Each task follows TDD: write tests first, then minimum implementation. Property-based tests use `hypothesis` and validate the 8 correctness properties from the design.

## Tasks

- [x] 1. Add hypothesis dev dependency and create module skeleton
  - Run `uv add --group dev hypothesis` to add hypothesis to the dev dependency group
  - Create empty `src/ghbot/processor.py` with module docstring
  - Create empty test files: `tests/unit/test_processor.py`, `tests/unit/test_info_processor.py`, `tests/unit/test_processor_props.py`
  - _Requirements: N/A (project setup)_

- [x] 2. Implement data types: ProcessingStatus, FeedbackEvent, RepoResult
  - [x] 2.1 Implement FeedbackEvent frozen dataclass
    - Write tests in `tests/unit/test_processor.py` for construction, field access, and immutability (frozen)
    - Implement `FeedbackEvent` as `@dataclass(frozen=True, slots=True)` with `type: str`, `severity: str`, `message: str` in `src/ghbot/processor.py`
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 2.2 Implement ProcessingStatus type alias and RepoResult dataclass
    - Write tests in `tests/unit/test_processor.py` for RepoResult construction with defaults, field mutation, errors list accumulation, and results dict population
    - Implement `ProcessingStatus = Literal["success", "partial", "failed"]` and `RepoResult` as `@dataclass(slots=True)` with fields: `owner: str`, `repo: str`, `status: ProcessingStatus = "success"`, `errors: list[str] = field(default_factory=list)`, `results: dict = field(default_factory=dict)`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [x] 3. Implement Monitor protocol and LoggingMonitor
  - [x] 3.1 Implement Monitor protocol
    - Write tests in `tests/unit/test_processor.py` for runtime-checkable isinstance verification: a conforming class passes, a non-conforming class fails
    - Implement `Monitor` as `@runtime_checkable class Monitor(Protocol)` with `async def send_event(self, event: FeedbackEvent) -> None`
    - _Requirements: 2.1, 2.5_

  - [x] 3.2 Implement LoggingMonitor
    - Write tests in `tests/unit/test_processor.py` for: isinstance check against Monitor, severity mapping (info→INFO, warning→WARNING, error→ERROR), unknown severity falls back to WARNING, logger name includes owner/repo, log message contains owner and repo context
    - Implement `LoggingMonitor` class with `__init__(self, owner: str, repo: str)` using `get_logger`, and `async def send_event` with severity-to-level mapping
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Write property test for severity-to-log-level mapping
    - **Property 2: Severity-to-log-level mapping**
    - Use `st.sampled_from(["info", "warning", "error"])` for severity, `st.text()` for type and message
    - Verify `LoggingMonitor.send_event` produces a log record at the corresponding Python logging level
    - **Validates: Requirements 3.2, 3.3, 3.4**

  - [x] 3.4 Write property test for log message context
    - **Property 3: Log message contains owner and repo context**
    - Use `st.text(min_size=1)` for owner/repo, `st.builds(FeedbackEvent)` for events
    - Verify log message contains both owner and repo strings
    - **Validates: Requirements 3.5**

- [x] 4. Implement RepoProcessor protocol
  - [x] 4.1 Implement RepoProcessor protocol
    - Write tests in `tests/unit/test_processor.py` for runtime-checkable isinstance: a conforming class (with `owner` property, `repo` property, `async def run() -> RepoResult`) passes isinstance check; a non-conforming class fails
    - Implement `RepoProcessor` as `@runtime_checkable class RepoProcessor(Protocol)` with `owner: str` property, `repo: str` property, and `async def run(self) -> RepoResult`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 4.2 Write property test for owner/repo construction round-trip
    - **Property 1: Owner/repo construction round-trip**
    - Use `st.text(min_size=1)` for owner and repo strings
    - Construct `InfoRepoProcessor` and verify `.owner` and `.repo` return the exact input strings
    - **Validates: Requirements 1.6**

- [x] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement InfoRepoProcessor constructor and properties
  - [x] 6.1 Implement InfoRepoProcessor constructor with validation
    - Write tests in `tests/unit/test_info_processor.py` for: empty owner raises ValueError, empty repo raises ValueError, valid construction stores owner/repo/gh/monitor, isinstance check against RepoProcessor passes
    - Implement `InfoRepoProcessor.__init__(self, owner, repo, gh, monitor)` with empty-string validation and private attribute storage; implement `owner` and `repo` as read-only properties
    - _Requirements: 1.6, 1.7, 1.8, 7.1_

- [x] 7. Implement InfoRepoProcessor.run() — happy path
  - [x] 7.1 Implement run() with progress events and all data-fetching steps (mocked GitHub API)
    - Write tests in `tests/unit/test_info_processor.py` for: run() sends start progress event, run() sends per-step progress events, run() sends finish progress event, run() returns RepoResult with status "success" and all 9 data point keys populated, owner and repo fields match constructor args
    - Implement `run()` method with `_fetch_repo_metadata`, `_fetch_file_count`, `_fetch_languages`, `_fetch_contributors`, `_fetch_latest_release`, `_fetch_open_pull_requests`, `_fetch_open_issues`, `_fetch_security_alerts` helper methods. Each helper calls `send_event` for progress, fetches via `github_api_call` context manager, and stores results in `RepoResult.results`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 7.2, 7.3_

  - [x] 7.2 Write property test for successful run fields
    - **Property 4: Successful run produces correct RepoResult fields**
    - Use `st.text(min_size=1)` for owner/repo, mock all GitHub API calls to succeed
    - Verify returned RepoResult has matching owner, repo, and status "success"
    - **Validates: Requirements 4.2**

  - [x] 7.3 Write property test for results dict completeness
    - **Property 8: Results dict completeness**
    - Use `st.text(min_size=1)` for owner/repo, mock all GitHub API calls to succeed
    - Verify results dict contains all 9 expected keys: `description`, `updated_at`, `file_count`, `languages`, `contributors`, `latest_release`, `open_pull_requests`, `open_issues`, `security_alerts`
    - **Validates: Requirements 7.2**

- [x] 8. Implement InfoRepoProcessor.run() — error handling
  - [x] 8.1 Implement per-step GitHubApiError resilience
    - Write tests in `tests/unit/test_info_processor.py` for: single step GitHubApiError → status "partial", error recorded, default value set, other steps still have valid data; multiple step failures → status "partial" with multiple errors
    - Implement error handling in each `_fetch_*` method: catch `GitHubApiError`, call `send_event` with severity "error", set sensible default, append to `result.errors`; after all steps, set status to "partial" if errors exist
    - _Requirements: 4.5, 6.1, 7.7, 7.8, 7.9_

  - [x] 8.2 Implement edge cases: no releases, empty languages, security alerts 403
    - Write tests in `tests/unit/test_info_processor.py` for: no releases → latest_release is None + warning event, empty languages → {} + warning event, security alerts 403 (GitHubNotFoundError) → [] + warning event
    - Implement specific handling in `_fetch_latest_release`, `_fetch_languages`, `_fetch_security_alerts` for these edge cases
    - _Requirements: 7.4, 7.5, 7.6_

  - [x] 8.3 Implement unexpected exception containment
    - Write tests in `tests/unit/test_info_processor.py` for: unexpected exception (e.g. RuntimeError) during processing → status "failed", error recorded, RepoResult returned (not raised)
    - Implement try/except in `run()` that catches non-FatalError exceptions, logs via monitor, sets status to "failed", and returns the RepoResult
    - _Requirements: 4.6, 6.2_

  - [x] 8.4 Implement FatalError propagation
    - Write tests in `tests/unit/test_info_processor.py` for: `GitHubPrimaryRateLimitError` raised during a step → re-raised from `run()`; `GitHubSecondaryRateLimitError` raised → re-raised from `run()`
    - Implement explicit re-raise of `FatalError` subclasses in `run()` before the general exception catch
    - _Requirements: 6.3_

  - [x] 8.5 Write property test for per-step error resilience
    - **Property 5: Per-step error resilience**
    - Use `st.sampled_from(DATA_POINT_STEPS)` to pick which step fails with `GitHubApiError`
    - Verify status is "partial", error is recorded, default is set for failed step, other steps have valid data
    - **Validates: Requirements 4.5, 6.1, 7.7, 7.9**

  - [x] 8.6 Write property test for unexpected exception containment
    - **Property 6: Unexpected exception containment**
    - Use `st.sampled_from([RuntimeError, ValueError, TypeError, KeyError])` for exception types
    - Verify status is "failed", error is recorded, RepoResult is returned without propagation
    - **Validates: Requirements 4.6, 6.2**

  - [x] 8.7 Write property test for FatalError propagation
    - **Property 7: FatalError propagation**
    - Use `st.sampled_from([GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError])` for exception types
    - Verify the exception is re-raised from `run()`
    - **Validates: Requirements 6.3**

- [x] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Wire InfoRepoProcessor into _main
  - [x] 10.1 Update _main to use InfoRepoProcessor and LoggingMonitor
    - Update tests in `tests/unit/test_main.py`: replace `process_repo` references with `InfoRepoProcessor` and `LoggingMonitor` construction; verify `_main` creates a `LoggingMonitor` and `InfoRepoProcessor` per repo and submits `processor.run` to the pool
    - Update `src/ghbot/__main__.py`: change import from `process_repo` to `InfoRepoProcessor, LoggingMonitor` from `ghbot.processor`; replace `pool.submit(process_repo, owner, repo, gh)` with `monitor = LoggingMonitor(owner, repo["name"])` / `processor = InfoRepoProcessor(owner, repo["name"], gh, monitor)` / `pool.submit(processor.run)`
    - Remove the `process_repo` function from `src/ghbot/github/repos.py` and its test from `tests/unit/test_repos.py`
    - _Requirements: 1.7, 4.1_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All tests follow TDD: write the test first (Red), then minimum implementation (Green), then refactor
- Use `AsyncMock` for all async mocks, patch at import site
- The `RecordingMonitor` test helper (a list-collecting stub) should be defined in `tests/unit/test_info_processor.py` for use in InfoRepoProcessor tests
