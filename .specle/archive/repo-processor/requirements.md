# Requirements Document

## Introduction

Replace the current `process_repo` stub in `src/ghbot/github/repos.py` with a protocol-based repository-processing architecture. `RepoProcessor` is the central protocol (runtime-checkable ABC) that defines the contract all repository processors must follow: read-only `owner` and `repo` attributes, acceptance of a Monitor, and an async `run` method returning a RepoResult. Concrete implementations such as `DependabotRepoProcessor`, `SecurityRepoProcessor`, or `PullRequestRepoProcessor` subclass or implement `RepoProcessor` to provide domain-specific processing logic.

The caller in `_main` constructs processor instances directly and submits `processor.run` to the `TaskPool`. The `TaskPool` does not need to know the concrete processor type — it calls `run()` on whatever is submitted. Multiple processor types can be queued concurrently, executing up to the configured concurrency limit, with the pool picking up the next task as each completes.

This spec defines the `RepoProcessor` protocol/base and supporting types (Monitor, Feedback_Event, RepoResult) so that concrete implementations can be built in future specs.

## Glossary

- **RepoProcessor**: The protocol/base class (runtime-checkable) that all repository processors implement. Defines the contract: read-only `owner` (str) and `repo` (str) attributes, acceptance of a Monitor, and an async `run() -> RepoResult` method. Concrete implementations — e.g. `DependabotRepoProcessor`, `SecurityRepoProcessor`, `PullRequestRepoProcessor` — subclass or satisfy this protocol to provide domain-specific processing logic.
- **Monitor**: An abstraction (protocol / ABC) through which a RepoProcessor reports events to the caller during processing. Exposes a single async `send_event` method that accepts a Feedback_Event.
- **Feedback_Event**: An object representing a single feedback occurrence. Contains a `type` (string identifying the event kind, e.g. `"progress"`, `"error"`), a `severity` (string indicating importance, e.g. `"info"`, `"warning"`, `"error"`), and a `message` (human-readable description).
- **RepoResult**: A structured type (dataclass) returned by a RepoProcessor's `run` method after processing completes. Contains first-class fields: `owner` (str), `repo` (str), `status` (Processing_Status), `errors` (list[str]), and `results` (dict) for processor-specific structured data.
- **TaskPool**: The existing concurrency manager (`src/ghbot/executor.py`) that schedules tasks with bounded parallelism. It accepts any async callable and does not depend on a specific processor type.
- **GitHub_API**: The `gidgethub.httpx.GitHubAPI` client used for all GitHub REST API interactions.
- **Processing_Status**: A string value indicating the outcome of processing — one of `"success"`, `"partial"`, or `"failed"`.
- **InfoRepoProcessor**: The first concrete implementation of the RepoProcessor protocol/base. Gathers repository summary statistics (description, last-changed date, file count, languages, contributors, latest release, open pull requests, open issues, security alerts) via the GitHub_API and returns them in a RepoResult, with the statistics stored in the `results` field.

## Requirements

### Requirement 1: RepoProcessor Protocol/Base

**User Story:** As a developer, I want a RepoProcessor protocol/base class that defines the contract for all repository processors, so that concrete implementations like DependabotRepoProcessor or SecurityRepoProcessor can be built against a consistent interface while the TaskPool and callers remain decoupled from specific types.

#### Acceptance Criteria

1. THE RepoProcessor protocol/base SHALL define a read-only `owner` attribute of type str.
2. THE RepoProcessor protocol/base SHALL define a read-only `repo` attribute of type str.
3. THE RepoProcessor protocol/base SHALL define an async method `run()` that returns a RepoResult.
4. THE RepoProcessor protocol/base SHALL be runtime-checkable so that callers can verify conformance using `isinstance`.
5. WHEN a class provides read-only `owner` and `repo` attributes and an async `run() -> RepoResult` method, THE RepoProcessor protocol/base SHALL recognise the class as a valid implementation without requiring explicit inheritance.
6. WHEN a RepoProcessor is created with an owner string and a repository name string, THE RepoProcessor SHALL store both values as read-only attributes accessible for the lifetime of the instance.
7. WHEN a RepoProcessor is created, THE RepoProcessor SHALL accept a GitHub_API client and a Monitor instance as constructor arguments.
8. IF an empty string is provided for owner or repository name, THEN THE RepoProcessor SHALL raise a `ValueError` with a message identifying the invalid argument.

### Requirement 2: Monitor Protocol

**User Story:** As a developer, I want a monitor abstraction with a single async method, so that processing can report typed, severity-tagged events without coupling to a specific output mechanism.

#### Acceptance Criteria

1. THE Monitor SHALL define a single async method `send_event(event: Feedback_Event)` for reporting all processing events.
2. THE Feedback_Event SHALL contain a `type` field (str) identifying the kind of event (e.g. `"progress"`, `"validation"`, `"fetch"`).
3. THE Feedback_Event SHALL contain a `severity` field (str) indicating the importance of the event, with allowed values `"info"`, `"warning"`, and `"error"`.
4. THE Feedback_Event SHALL contain a `message` field (str) providing a human-readable description of the event.
5. WHEN `send_event` is called, THE Monitor SHALL accept the event without blocking the caller's async task.

### Requirement 3: Logging Monitor

**User Story:** As a developer, I want a default monitor backed by the existing logging infrastructure, so that processing feedback is captured in logs without additional configuration.

#### Acceptance Criteria

1. THE LoggingMonitor SHALL implement the Monitor protocol.
2. WHEN `send_event` is called with a Feedback_Event whose severity is `"info"`, THE LoggingMonitor SHALL log the message at INFO level using the project's `get_logger` utility.
3. WHEN `send_event` is called with a Feedback_Event whose severity is `"warning"`, THE LoggingMonitor SHALL log the message at WARNING level.
4. WHEN `send_event` is called with a Feedback_Event whose severity is `"error"`, THE LoggingMonitor SHALL log the message at ERROR level.
5. WHEN the LoggingMonitor is created, THE LoggingMonitor SHALL include the owner and repository name as context in every log message.

### Requirement 4: Processing Execution

**User Story:** As a developer, I want a RepoProcessor implementation to execute processing asynchronously and return a RepoResult, so that repository data is collected and returned in a structured format.

#### Acceptance Criteria

1. THE RepoProcessor SHALL provide an async `run` method that performs processing and returns a RepoResult, fulfilling the RepoProcessor protocol/base contract.
2. WHEN `run` completes successfully, THE RepoResult SHALL have the `owner` field set to the owner string, the `repo` field set to the repository name string, and the `status` field set to the Processing_Status value `"success"`.
3. WHEN `run` begins execution, THE RepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of type `"progress"`, severity `"info"`, and a message indicating processing has started.
4. WHEN `run` completes execution, THE RepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of type `"progress"`, severity `"info"`, and a message indicating processing has finished.
5. WHEN `run` encounters a non-fatal error during a processing step, THE RepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of severity `"error"`, record the error in the RepoResult `errors` field (list of strings), and set the `status` field to the Processing_Status value `"partial"`.
6. IF `run` encounters a fatal error that prevents further processing, THEN THE RepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of severity `"error"`, set the `status` field to the Processing_Status value `"failed"`, and return the RepoResult with the error information rather than raising an exception.

### Requirement 5: RepoResult Structured Type

**User Story:** As a developer, I want a well-defined structured result type with first-class fields, so that downstream consumers can reliably access processing outcomes via typed attributes rather than dict key lookups.

#### Acceptance Criteria

1. THE RepoResult SHALL be a structured type (dataclass) with a first-class `owner` field of type str containing the owner string value.
2. THE RepoResult SHALL have a first-class `repo` field of type str containing the repository name string value.
3. THE RepoResult SHALL have a first-class `status` field of type Processing_Status containing the processing outcome.
4. THE RepoResult SHALL have a first-class `errors` field of type list[str] containing error message strings collected during processing.
5. WHEN no errors occurred during processing, THE RepoResult `errors` field SHALL be an empty list.
6. THE RepoResult SHALL have a first-class `results` field of type dict containing processor-specific structured data.

### Requirement 6: Error Resilience During Processing

**User Story:** As a developer, I want a RepoProcessor implementation to handle errors gracefully, so that a failure in one processing step does not crash the entire scan.

#### Acceptance Criteria

1. IF a `GitHubApiError` is raised during processing, THEN THE RepoProcessor SHALL catch the error, report it via `send_event` on the Monitor with a Feedback_Event of severity `"error"`, and continue with remaining processing steps.
2. IF an unexpected exception is raised during processing, THEN THE RepoProcessor SHALL catch the error, report it via `send_event` on the Monitor with a Feedback_Event of severity `"error"`, set the Processing_Status to `"failed"`, and return the RepoResult.
3. THE RepoProcessor SHALL propagate only exceptions from the existing error hierarchy (`FatalError` and its subclasses that indicate abort-level conditions) to the TaskPool for handling by its error-management logic.

### Requirement 7: InfoRepoProcessor — Repository Summary Statistics

**User Story:** As a developer, I want an initial RepoProcessor implementation that gathers repository summary statistics, so that I can verify the protocol/base design end-to-end and provide a useful overview of any repository.

#### Acceptance Criteria

1. THE InfoRepoProcessor SHALL implement the RepoProcessor protocol/base.
2. WHEN `run` is called, THE InfoRepoProcessor SHALL collect the following statistics via the GitHub_API and store them in the RepoResult `results` field:
   - `description` — the repository description string.
   - `updated_at` — the date the repository was last changed.
   - `file_count` — the number of files in the repository.
   - `languages` — the language breakdown returned by the GitHub_API.
   - `contributors` — the list of contributors to the repository.
   - `latest_release` — the latest release information.
   - `open_pull_requests` — the count of open pull requests.
   - `open_issues` — the count of open issues.
   - `security_alerts` — the Dependabot or security alerts for the repository.
3. WHEN the InfoRepoProcessor begins collecting each data point, THE InfoRepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of type `"progress"` and severity `"info"` indicating which data point is being fetched.
4. IF the GitHub_API returns no releases for the repository, THEN THE InfoRepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of severity `"warning"` indicating no releases are available, and SHALL set `latest_release` to `null` in the `results` field.
5. IF the GitHub_API returns an empty response for the languages endpoint, THEN THE InfoRepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of severity `"warning"` indicating no language data is available, and SHALL set `languages` to an empty dict in the `results` field.
6. IF the GitHub_API denies access to security alerts (e.g. insufficient permissions), THEN THE InfoRepoProcessor SHALL call `send_event` on the Monitor with a Feedback_Event of severity `"warning"` indicating security alerts are inaccessible, and SHALL set `security_alerts` to an empty list in the `results` field.
7. IF any individual data-gathering step raises a `GitHubApiError`, THEN THE InfoRepoProcessor SHALL catch the error, call `send_event` on the Monitor with a Feedback_Event of severity `"error"`, set a sensible default for that data point (`null`, empty list, or `0`), and continue collecting the remaining data points.
8. WHEN all data points have been collected successfully, THE RepoResult SHALL have a `status` field with the Processing_Status value `"success"`.
9. WHEN one or more data points fell back to defaults due to errors or unavailability, THE RepoResult SHALL have a `status` field with the Processing_Status value `"partial"` and the `errors` field SHALL list the corresponding error messages.
