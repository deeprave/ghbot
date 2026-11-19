# Rate-limit resilience spike

## Question

What changes are required for ghbot to honour GitHub rate-limit delays globally, bound waits, and preserve complete repository results in an incomplete report without silently losing work?

## Investigation approach

- Trace REST and GraphQL rate-limit classification from `github_api_call()` into `TaskPool`.
- Inspect the runner lifecycle to determine when reports can be rendered and written.
- Evaluate the concurrency and cancellation boundaries needed to pause all workers safely.
- Compare the requested partial-result contract with existing explicit-repository selection and combined-report composition.

## Findings

1. `github_api_call()` identifies primary REST limits through `gidgethub.RateLimitExceeded`, primary GraphQL limits through structured codes or client rate-limit state, and secondary limits through HTTP 429, structured GraphQL signals, or a narrow message fallback. The custom error classes carry no response headers or normalized delay.
2. `TaskPool` aborts immediately for a primary limit. For a secondary limit it sleeps a fixed 60 seconds inside the failing worker and retries once. Other workers are neither paused nor prevented from sending more requests.
3. `TaskPool.__aexit__()` raises before `run_mode()` and `run_combo()` return their collections. Mode commands therefore cannot render or write completed results after a fatal limit.
4. Pool results are appended only after a full repository task returns. This naturally supports the requested whole-repository rule, but the runner currently has no requested-repository ledger from which to construct `not_processed` entries.
5. Explicit repository selection provides a rerun input path, but currently drops unresolved or archived repositories; that is separately addressed by issue #50. The spike must not assume #50 is implemented.
6. Combined reports compose complete collection documents only after the pool exits. A partial-result envelope must be owned by the runner/report boundary and applied consistently to standalone and combined JSON documents.

## Recommendations

1. Perform a focused design for a shared asynchronous rate-limit gate owned by the pool or runner. It needs one authoritative `blocked_until`, a lock/condition around request admission, and injected clock/sleep functions for deterministic tests.
2. Extend rate-limit errors with a normalized delay and reset timestamp at the GitHub client boundary. Prefer `Retry-After`; otherwise use reset time when available; use the documented 60-second secondary fallback only when neither is available.
3. Add configurable `max-rate-wait` and `max-rate-limit-hits`, defaulting to 120 seconds and 3 respectively, after confirming configuration/CLI conventions in design.
4. Separate fatal-pool completion from report rendering so the caller receives completed repository results plus an abort record, then exits non-zero only after writing the marked incomplete report.
5. Track every repository accepted for processing and classify any unfinished entry as `rate_limited`; do not emit in-flight partial repository records.
6. Make the subsequent feature spec depend on the schema contract in #48 for versioned `complete`, `abort_reason`, and `not_processed` JSON fields. Keep consumer-side resume/import convenience out of scope.

## Risks

- A gate acquired only after a request starts cannot prevent concurrent requests already in flight; cancellation and the requested grace period need precise ownership.
- gidgethub exception objects may not consistently expose headers, so the client boundary may need a transport-level response inspection seam.
- Returning partial collections while preserving existing fatal-error semantics affects every standalone command and combo orchestration.
- Cancellation order must not violate the union invariant: each requested repository appears exactly once in either completed repositories or `not_processed`.

## Estimated implementation effort

**XL.** This spans API error translation, concurrent scheduling, configuration, report contracts, command exit behaviour, package schemas, and deterministic asynchronous tests.
