# Requirements: rate-limit resilience

## Introduction

When GitHub limits a run, ghbot currently either aborts immediately or retries one worker while
others continue issuing requests. Completed results are then lost. The release needs bounded,
global backoff and a durable incomplete-report contract.

## Glossary

- **rate-limit gate**: shared admission control that pauses new GitHub requests during a wait.
- **fatal rate limit**: a limit whose wait exceeds policy or whose allowed wait count is exhausted.
- **complete repository**: a repository whose collection work finished before an abort.
- **not processed**: a requested repository that did not complete because the run stopped.
- **terminal repository**: a repository whose task reached a handled, non-result outcome (for
  example, GitHub reported it unavailable) and therefore is not awaiting rate-limit recovery.

## Requirements

### Requirement 1: Honour GitHub rate-limit delays globally

**User Story:** As an operator, I want ghbot to wait for reasonable GitHub limits without causing
additional requests, so a run can recover safely.

#### Acceptance Criteria

1. WHEN GitHub reports a primary or secondary rate limit with a wait within policy, THE rate-limit gate SHALL pause all new GitHub requests until that wait ends and retry the affected request with a bounded random delay of up to five seconds.
2. THE client SHALL prefer `Retry-After`, otherwise use a rate-limit reset time, and otherwise use a 60-second fallback for every recognized primary or secondary limit, including GraphQL limits without timing metadata.
3. THE one shared gate SHALL apply to REST and GraphQL rate-limit signals, so a limit from either API pauses both request types.
4. THE run SHALL log each wait with its reason, duration, and reset time when available, without logging credentials or response headers.
5. THE final run statistics SHALL include the number of shared rate-limit episodes and their total
   shared wait duration.

### Requirement 2: Bound rate-limit recovery

**User Story:** As an operator, I want predictable limits on waiting, so scheduled runs do not hang indefinitely.

#### Acceptance Criteria

1. THE configuration and CLI SHALL provide `max-rate-wait` and `max-rate-limit-hits` controls, defaulting to 120 seconds and 3 rate-limit episodes.
2. IF a required wait exceeds `max-rate-wait`, THEN the run SHALL stop as a fatal rate-limit failure.
3. IF the rate-limit episode count exceeds `max-rate-limit-hits`, THEN the run SHALL stop as a fatal rate-limit failure. Multiple in-flight requests that fail while one shared block is active SHALL count as one episode.
4. IF an active episode is extended, THEN its total duration from the first block through the
   extension SHALL remain within `max-rate-wait`; otherwise the run SHALL stop as a fatal
   rate-limit failure.
5. IF `max-rate-wait` is zero, THEN every rate-limit signal SHALL stop the run without retrying,
   including a signal whose advertised delay is zero.

### Requirement 3: Preserve explicit incomplete results

**User Story:** As a consumer, I want an aborted run to retain finished repository results and identify every missing repository, so I never mistake partial data for a complete report.

#### Acceptance Criteria

1. ON a fatal rate limit, THE run SHALL stop admitting repositories, allow a bounded grace period for in-flight work, and cancel unfinished work.
2. THE JSON report SHALL retain only completed repository results and SHALL set `complete` to `false`, `abort_reason` to `rate_limited`, and `not_processed` to each unfinished requested repository with reason `rate_limited`.
3. EACH requested repository SHALL appear exactly once across completed results and `not_processed`; in-flight repositories SHALL NOT produce partial records.
4. THE combined report SHALL be incomplete when any contained report is incomplete.
5. THE command SHALL write the incomplete report before exiting non-zero with a documented, distinct rate-limit exit status.
6. IF discovery is interrupted by a fatal rate limit, THEN every explicitly selected `--repo`
   repository SHALL be represented in the resulting completed or `not_processed` ledger, even if
   discovery had not yet yielded it.
7. IF an ordinary task failure prevents a repository from completing, THEN the report SHALL be
   incomplete with non-rate-limit failure metadata; handled unavailable repositories SHALL remain
   terminal rather than being labelled rate limited by a concurrent abort.
8. A combined report SHALL preserve a section result exactly once when a later section retries or
   is interrupted; each section SHALL identify only repositories unfinished for that section.
9. A combined section whose requested repositories all completed or became terminal SHALL remain
   complete even when another section makes the combined wrapper incomplete.

### Requirement 4: Preserve report and schema contracts

**User Story:** As a JSON consumer, I want the incomplete-result fields documented in the installed schemas, so I can validate and handle an interrupted run.

#### Acceptance Criteria

1. THE current unreleased `1.0` schema resources SHALL represent `complete`, `abort_reason`, and `not_processed`; schema versions SHALL advance only after a published release establishes the prior contract.
2. Plain and table output SHALL preserve existing successful-run behaviour.
3. README documentation SHALL describe the controls, incomplete-result semantics, exit status, and rerunning `not_processed` repositories.

## Non-Functional Requirements

- Preserve existing non-rate-limit error handling and authentication behaviour.
- Keep waiting asynchronous; tests use injected time control and never sleep in real time.
- Cover primary and secondary REST/GraphQL limits, global request pausing, concurrent failures within one episode, jittered retry release, policy exhaustion, whole-repository results, combined reports, schemas, and exit status.
- Implement this issue as GitHub issue #51; a delivery PR SHALL include `Closes #51`.
- Do not advance the package or schema version while the `1.0.0` release remains unpublished.
