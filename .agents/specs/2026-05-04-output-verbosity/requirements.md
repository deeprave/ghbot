# Requirements Document

## Introduction

ghbot currently emits log messages at levels that don't match their actual significance. Empty-state
conditions (no releases, no languages, inaccessible security alerts) are logged as `WARNING`, which
implies a problem requiring attention. Per-step fetch progress events are logged at `INFO`, adding
noise at the default console level. HTTP request/response details are mixed into the general
`--verbose`/`--quiet` verbosity axis rather than being independently opt-in.

This feature corrects the log-level assignments across `LoggingMonitor`, `InfoRepoProcessor`, and
`github_api_call` so that the console output at each verbosity level contains only the messages a
human operator actually needs at that level. It also introduces a `--requests` CLI flag that gates
HTTP-layer logging independently of the general verbosity controls.

## Glossary

- **LoggingMonitor**: The concrete `Monitor` implementation in `processor.py` that translates
  `FeedbackEvent` objects into Python log calls.
- **InfoRepoProcessor**: The concrete `RepoProcessor` in `processor.py` that orchestrates the
  per-repository fetch steps and emits `FeedbackEvent`s via its `Monitor`.
- **FeedbackEvent**: An immutable dataclass carrying `type`, `severity`, and `message` fields,
  produced by `InfoRepoProcessor` and consumed by `LoggingMonitor`.
- **Console_Level**: The effective log level applied to the stderr console handler, controlled by
  `--verbose` (debug), `--quiet` (warn), or the default (info).
- **Requests_Logger**: A dedicated Python logger (name `ghbot.requests`) used exclusively for
  HTTP request and response detail lines.
- **Empty_State**: A condition where a GitHub API call succeeds but returns no data — for example,
  a repository with no releases, no language data, or inaccessible security alerts. This is normal
  and expected for many repositories.
- **Processing_Started**: The `FeedbackEvent` emitted at the beginning of `InfoRepoProcessor.run()`,
  before any fetch steps execute.
- **Processing_Finished**: The `FeedbackEvent` emitted at the end of `InfoRepoProcessor.run()`,
  after all fetch steps complete.

## Requirements

### Requirement 1: Empty-state conditions logged at debug

**User Story:** As an operator running ghbot against a large set of repositories, I want
empty-state conditions (no releases, no language data, inaccessible security alerts) to appear only
at debug level, so that the default console output is not cluttered with messages that indicate
nothing is wrong.

#### Acceptance Criteria

1. WHEN `_fetch_latest_release` receives a `GitHubNotFoundError`, THE `InfoRepoProcessor` SHALL
   emit a `FeedbackEvent` with `severity` set to `"debug"` and a message indicating no releases
   are available.
2. WHEN `_fetch_languages` receives an empty response from the GitHub API, THE `InfoRepoProcessor`
   SHALL emit a `FeedbackEvent` with `severity` set to `"debug"` and a message indicating no
   language data is available.
3. WHEN `_fetch_languages` receives a `GitHubNotFoundError`, THE `InfoRepoProcessor` SHALL emit a
   `FeedbackEvent` with `severity` set to `"debug"` and a message indicating the languages endpoint
   is not accessible.
4. WHEN `_fetch_security_alerts` receives a `GitHubNotFoundError`, THE `InfoRepoProcessor` SHALL
   emit a `FeedbackEvent` with `severity` set to `"debug"` and a message indicating security alerts
   are inaccessible.
5. WHEN a fetch step returns data, THE `InfoRepoProcessor` SHALL emit no `FeedbackEvent` for that
   empty-state condition (the absence of a warning is the signal that data was returned).

### Requirement 2: Per-step fetch progress events logged at debug

**User Story:** As an operator, I want per-step fetch progress messages (e.g. "fetching open pull
requests") to appear only at debug level, so that the default console output shows meaningful
progress without per-field noise.

#### Acceptance Criteria

1. WHEN `InfoRepoProcessor` begins any individual fetch step (`_fetch_repo_metadata`,
   `_fetch_file_count`, `_fetch_languages`, `_fetch_contributors`, `_fetch_latest_release`,
   `_fetch_open_pull_requests`, `_fetch_open_issues`, `_fetch_security_alerts`), THE
   `InfoRepoProcessor` SHALL emit a `FeedbackEvent` with `severity` set to `"debug"`.
2. THE `LoggingMonitor` SHALL map a `FeedbackEvent` with `severity` `"debug"` to a Python
   `logging.DEBUG` call.

### Requirement 3: Processing lifecycle events at appropriate levels

**User Story:** As an operator, I want to see when a repository starts processing at info level so
I can track progress in real time, and have the completion message suppressed at the default level
since it adds no new information once the start was shown.

#### Acceptance Criteria

1. WHEN `InfoRepoProcessor.run()` begins, THE `InfoRepoProcessor` SHALL emit a `FeedbackEvent`
   with `type` `"progress"` and `severity` `"info"` and a message indicating processing has
   started.
2. WHEN `InfoRepoProcessor.run()` completes, THE `InfoRepoProcessor` SHALL emit a `FeedbackEvent`
   with `type` `"progress"` and `severity` `"debug"` and a message indicating processing has
   finished.

### Requirement 4: HTTP request/response details gated by --requests flag

**User Story:** As a developer debugging API interactions, I want to opt in to HTTP request and
response detail logging via a dedicated `--requests` flag, so that this low-level detail is never
shown during normal operation regardless of `--verbose` or `--quiet`.

#### Acceptance Criteria

1. THE `CLI` SHALL accept a `--requests` boolean flag (default: `False`) that enables HTTP-layer
   logging independently of `--verbose` and `--quiet`.
2. WHEN `--requests` is not passed, THE `CLI` SHALL suppress all output from the
   `Requests_Logger`, regardless of the `--verbose` or `--quiet` setting.
3. WHEN `--requests` is passed, THE `CLI` SHALL enable the `Requests_Logger` at `debug` level on
   the console handler.
4. WHERE HTTP request/response detail logging is implemented, THE `github_api_call` context manager
   (or its callers) SHALL route those messages through the `Requests_Logger` rather than the
   general application logger.
5. THE `LoggingMonitor` SHALL NOT route any `FeedbackEvent` through the `Requests_Logger`; the
   `Requests_Logger` is reserved for the HTTP layer only.

### Requirement 5: LoggingMonitor supports debug severity

**User Story:** As a developer extending ghbot, I want `LoggingMonitor` to correctly handle
`FeedbackEvent` objects with `severity` `"debug"`, so that new debug-level events are routed to
the right log level without requiring changes to the monitor.

#### Acceptance Criteria

1. THE `LoggingMonitor` SHALL map `FeedbackEvent.severity` `"debug"` to a Python `logging.DEBUG`
   call.
2. THE `LoggingMonitor` SHALL map `FeedbackEvent.severity` `"info"` to a Python `logging.INFO`
   call.
3. THE `LoggingMonitor` SHALL map `FeedbackEvent.severity` `"warning"` to a Python `logging.WARNING`
   call.
4. THE `LoggingMonitor` SHALL map `FeedbackEvent.severity` `"error"` to a Python `logging.ERROR`
   call.
5. IF `LoggingMonitor` receives a `FeedbackEvent` with an unrecognised `severity`, THEN THE
   `LoggingMonitor` SHALL fall back to `logging.WARNING` to ensure the message is not silently
   dropped.
