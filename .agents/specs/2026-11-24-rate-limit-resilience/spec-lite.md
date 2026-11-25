# Rate-limit resilience

## Problem

GitHub rate limits either abort ghbot immediately or leave other workers making requests. A fatal
limit drops every completed result.

## Goal

Use a shared asynchronous rate-limit gate to pause REST and GraphQL requests for short, server-directed waits and
release retries with bounded jitter. Bound the whole lifetime of a shared episode, publish aggregate wait statistics,
and make the wait duration and episode count configurable. If recovery is no longer reasonable, preserve only whole
completed repository or section results in an explicitly incomplete report and exit with a distinct failure.

## Output contract

Incomplete JSON has `complete: false`, a reason-specific `abort_reason` (`rate_limited` or
`task_failed`), and `not_processed` entries. Every requested repository appears exactly once in
completed results or `not_processed`; handled unavailable repositories are terminal. Explicit
`--repo` selections remain accountable even if discovery is rate-limited. The same contract applies
to combined output and the current unreleased `1.0` schemas. Versions advance only after a release
is published.

## Design direction

The GitHub client normalizes rate-limit delay data, including GraphQL HTTP rate-limit responses and
secondary REST reset headers when present.
Runner or pool-owned admission control gates REST and GraphQL requests globally and rechecks after
retry jitter; a zero wait policy permits no retry. Missing limit timing uses a 60-second fallback. The report boundary receives
completed, terminal, failed, and per-section results with abort data, writes output, then returns
the distinct failure status.

## Verification

Use fake clocks and transports to cover primary/secondary limits, GraphQL HTTP classification,
fractional reset waits, fatal-abort cancellation, renewed blocks, bounded episode extensions,
global pause, exact repository/section classification, standalone and combined
JSON/schema output, and the exit status.
