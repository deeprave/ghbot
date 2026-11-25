# Design: rate-limit resilience

## Overview

Add a per-run asynchronous rate-limit gate. Every wrapped GitHub REST or GraphQL call waits at the
gate before starting. A normalized rate-limit error blocks the gate, then retries the failed
repository work when within policy. A policy breach stops scheduling, settles or cancels in-flight
repository tasks, and returns an outcome that commands can render before returning a distinct
failure status.

## Architecture

```text
GitHub response
  -> github_api_call() classifies limit + normalizes delay/reset
  -> RateLimitGate records the shared blocked-until time and hit count
  -> TaskPool retries the affected repository or records a rate-limit abort
  -> runner records completed and requested repository identities
  -> command renders a complete or incomplete standalone/combined report, then exits
```

### Client and gate

- Extend the two existing rate-limit error types with a normalized `delay_seconds`, optional
  `reset_at`, and limit kind. `github_api_call()` derives these in order: `Retry-After`, reset
  time, then a 60-second fallback for every recognized limit. It recognizes REST and GraphQL
  signals, including GraphQL HTTP 403/429 `BadGraphQLRequest` responses and documented
  secondary-limit message variants; GraphQL primary limits without reset metadata use that
  fallback instead of aborting. Only recognized limit signals take this path.
- Create a `RateLimitGate` owned by a runner invocation. It has an async lock/condition,
  fractional-second `blocked_until`, episode start, episode count, aggregate shared wait duration,
  and injected monotonic clock/sleep/random functions for deterministic tests. Reset-time deltas
  retain fractional seconds; configuration remains in non-negative whole seconds. The first limit that establishes
  a future block consumes one episode; concurrent failures while that block remains active join it
  without consuming another. An extension is rejected when the elapsed episode span exceeds
  `max-rate-wait`. Admission loops until no block remains, rechecks after its zero-to-five-second
  retry jitter, and waits again if another caller renewed the block.
- A zero `max-rate-wait` is an explicit no-retry policy: the gate rejects every rate-limit signal,
  including a zero-delay response, before it creates an episode.
- Give the shared GitHub client the gate for the duration of a runner invocation, so the existing
  `github_api_call()` boundary gates repository discovery as well as processor REST and GraphQL
  calls. No token, header, or payload is logged.
- `max-rate-wait` and `max-rate-limit-hits` enter `DEFAULTS`, TOML merging, and root Click options
  as `--max-rate-wait` and `--max-rate-limit-hits`, with defaults of 120 and 3. Invalid values are
  rejected as Click usage errors.

### Pool and runner outcome

- Replace the rate-limit path that raises from `TaskPool.__aexit__` with a `PoolOutcome` containing
  completed, terminal, and failed task identities, statistics, and an optional `RateLimitAbort`.
  Existing authentication, network-threshold, and other fatal errors retain their current
  propagation behaviour. `submit()` rechecks abort state after acquiring capacity so no queued
  work starts after a concurrent abort.
- A policy breach signals the pool abort immediately, including active discovery. `TaskPool.__aexit__`
  observes that signal even when it begins before a worker detects the breach, gives already-running
  tasks a fixed internal grace period, then cancels unfinished tasks. Retry paths recheck abort state
  before recording, after waiting, and before issuing another request. The caller records every
  discovered identity; on a discovery abort it also adds configured explicit selections to the
  requested ledger, comparing identities case-insensitively and excluding explicit selections known
  to be unavailable or archived. Terminal unavailable identities are excluded from rate-limited
  output, while unexpected task failures are represented with `task_failed` metadata. No partial
  repository result is emitted.
- `run_processor()` returns completion metadata so `info` also surfaces a fatal rate-limit exit.
  `run_mode()` returns a report outcome rather than losing its collection on a rate-limit abort.
  `run_combo()` commits each completed section result immediately and records per-section completed
  identities, so retries neither duplicate completed sections nor discard them after a later
  section aborts. Each nested section derives its own completion state from its per-mode ledger;
  the combined wrapper is incomplete if any contained section is incomplete.

## API and data

### Configuration

```toml
max-rate-wait = 120
max-rate-limit-hits = 3
```

Both values are non-negative integers; zero means no wait or retry is accepted.

### Incomplete standalone JSON

Successful documents keep their existing shape. A rate-limited document adds the following
additive fields:

```json
{
  "complete": false,
  "abort_reason": "rate_limited",
  "not_processed": [
    {"repository": "owner/repo", "reason": "rate_limited"}
  ]
}
```

`repositories` contains only whole completed records. A non-rate task failure uses
`abort_reason: "task_failed"` and `not_processed` entries with the same reason. On complete runs,
`complete` is `true`, `abort_reason` is `null`, and `not_processed` is empty, providing a stable
envelope for consumers. Plain and table output retain their successful-run content; incomplete
output receives a concise reason-specific banner.

### Combined JSON and schemas

- Add the same completion fields to each nested report and to the combined wrapper. The wrapper’s
  `not_processed` is the ordered union of repositories unfinished by any nested report.
- The `1.0.0` package is unreleased, so amend the current `1.0.json` resources for security,
  issues, drift, and combined reports. Keep their canonical IDs at `1.0`; do not create `1.1`
  resources until a later published-release change requires a new contract.
- Each current schema constrains the completion fields while retaining `additionalProperties`
  support. The combined schema constrains the wrapper and its referenced sections.

## Error handling

| Condition | Policy |
| --- | --- |
| Delay within both limits | Globally block, log safe diagnostics, retry the failed request. |
| Delay exceeds `max-rate-wait` | Stop gracefully and emit incomplete output. |
| Episode extension exceeds `max-rate-wait` | Stop gracefully and emit incomplete output. |
| Episode count exceeds `max-rate-limit-hits` | Stop gracefully and emit incomplete output. |
| In-flight task finishes in grace period | Include its whole repository result. |
| In-flight task exceeds grace period | Cancel it and list the repository as `rate_limited`. |
| Unexpected task failure | Emit incomplete output with `task_failed` metadata. |
| Non-rate-limit `FatalError` | Preserve current propagation and exit behaviour. |
| Output write failure | Preserve existing Click output error behaviour. |

Use a dedicated `RateLimitAbortError` with a documented non-zero exit code distinct from generic
fatal errors; commands write the rendered outcome before logging the error and exiting with it.

## Report rendering

Mode and combo commands receive an outcome, render it in the selected format, write it, and only
then raise the dedicated rate-limit exit. Existing successful plain, table, and JSON rendering
remains unchanged except for the explicit complete-run envelope fields in JSON.

README documents the global backoff policy, defaults, exit code, incomplete JSON fields, and the
use of `not_processed` repository values with `--repo` for a follow-up run.

## Test strategy

- Client tests cover REST and GraphQL primary/secondary classification and delay precedence,
  including secondary response reset data without `Retry-After`.
- Gate/pool tests use fake monotonic time and sleeper hooks to prove post-jitter renewal waiting,
  bounded episode extensions, fractional reset waits, admission-stop rechecks, aggregate statistics,
  and cancellation after grace without real sleeps.
- Runner tests cover explicit selections during discovery abort, terminal unavailable identities,
  unexpected task failures, whole-repository results, and preservation of unrelated fatal errors.
- Mode and combo tests cover `info` failure propagation, exactly-once section retention across
  retries/aborts, rendered reason-specific incomplete output, and JSON-schema validation.
- Config/CLI tests cover defaults, TOML values, overrides, and validation. Run the project’s full
  pytest, Ruff, Ty, and format gates through `uv run`.
