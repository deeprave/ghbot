# Tasks: rate-limit resilience

- [x] 1. Normalize rate-limit policy and client signals (`src/ghbot/errors.py`, `src/ghbot/github/client.py`, `src/ghbot/config.py`, `src/ghbot/__main__.py`, `tests/unit/test_client.py`, `tests/unit/test_main.py`)
  - [x] 1.1 Add focused failing tests for REST/GraphQL delay precedence, defaults, config/CLI overrides, and invalid policy values.
  - [x] 1.2 Add normalized rate-limit error data and the `max-rate-wait` / `max-rate-limit-hits` configuration and CLI controls.

- [x] 2. Add shared asynchronous request admission (`src/ghbot/rate_limit.py`, `src/ghbot/github/client.py`, `src/ghbot/runner.py`, `tests/unit/test_rate_limit.py`, `tests/unit/test_client.py`)
  - [x] 2.1 Add fake-clock tests proving global admission pauses requests after primary and secondary limits without real sleeps.
  - [x] 2.2 Implement the per-run gate and attach it to the shared GitHub client for discovery, REST, and GraphQL calls.

- [x] 3. Preserve pool outcomes on fatal rate limits (`src/ghbot/executor.py`, `src/ghbot/errors.py`, `tests/unit/test_executor.py`)
  - [x] 3.1 Add failing pool tests for bounded retries, policy exhaustion, admission stop, grace completion, cancellation, and non-rate fatal-error preservation.
  - [x] 3.2 Return a rate-limit abort outcome with completed identities while retaining existing handling for unrelated fatal errors.

- [x] 4. Render incomplete standalone reports before the distinct exit (`src/ghbot/runner.py`, `src/ghbot/report_style.py`, `src/ghbot/modes/{security,issues,drift}.py`, `tests/unit/test_runner.py`, `tests/unit/test_*_report_mode.py`)
  - [x] 4.1 Add failing mode/runner tests for whole-repository accounting, incomplete JSON fields, plain/table banners, and write-before-exit behaviour.
  - [x] 4.2 Add report outcomes, repository ledgers, incomplete rendering, and the dedicated rate-limit exit path.

- [x] 5. Apply incomplete semantics to combined output and current schemas (`src/ghbot/combo.py`, `src/ghbot/report_style.py`, `src/ghbot/schemas/**/*.json`, `tests/unit/test_combo.py`, `tests/unit/test_report_schemas.py`)
  - [x] 5.1 Add failing combined-report and schema-validation tests for wrapper/section completion state and per-mode `not_processed` entries.
  - [x] 5.2 Implement combined outcome rendering and amend only the unreleased `1.0` schema resources.

- [x] 6. Document rate-limit recovery (`README.md`)
  - [x] 6.1 Document controls, defaults, incomplete-report fields, the distinct exit status, and rerunning `not_processed` repositories with explicit selection.

- [x] 7. Coalesce concurrent limits and stagger retry release (`src/ghbot/rate_limit.py`, `tests/unit/test_rate_limit.py`, `README.md`)
  - [x] 7.1 Add failing fake-clock tests showing concurrent failures share one episode and retry waiters receive bounded jitter.
  - [x] 7.2 Implement episode coalescing and injected bounded retry jitter; clarify the policy documentation.

- [x] 8. Recover from GraphQL limits without timing metadata (`src/ghbot/github/client.py`, `tests/unit/test_client.py`)
  - [x] 8.1 Add failing REST/GraphQL tests for the shared 60-second fallback and global-gate behaviour.
  - [x] 8.2 Normalize every recognized timing-less rate limit to the fallback rather than aborting.

- [x] 9. Correct rate-limit admission and repository ledgers (`src/ghbot/executor.py`, `src/ghbot/runner.py`, `tests/unit/test_executor.py`, `tests/unit/test_runner.py`)
  - [x] 9.1 Add focused failing tests for post-acquire aborts, discovery stopping before another yield, explicit `--repo` accounting on discovery abort, and terminal unavailable identities.
  - [x] 9.2 Recheck pool admission after capacity acquisition, stop discovery immediately on abort, and distinguish completed, terminal, and unfinished task identities in standalone reports.

- [x] 10. Preserve accurate incomplete mode and combined reports (`src/ghbot/runner.py`, `src/ghbot/report_style.py`, `src/ghbot/modes/info.py`, `src/ghbot/schemas/**/*.json`, `tests/unit/test_runner.py`, `tests/unit/test_report_composition.py`, `tests/unit/test_main.py`)
  - [x] 10.1 Add focused failing tests for info’s rate-limit exit, `task_failed` output metadata, and exactly-once completed combo sections when a later section retries or aborts.
  - [x] 10.2 Propagate processor completion to info, render reason-specific incomplete outcomes, preserve per-mode completion ledgers, and extend the unreleased schemas for `task_failed`.

- [x] 11. Make shared-rate episodes renewal-safe and observable (`src/ghbot/rate_limit.py`, `src/ghbot/executor.py`, `tests/unit/test_rate_limit.py`, `tests/unit/test_executor.py`)
  - [x] 11.1 Add fake-time tests for renewed blocks during retry jitter, extension rejection beyond the episode budget, and shared episode count and wait-duration statistics.
  - [x] 11.2 Recheck the gate after jitter, bound full episode lifetime, and include aggregate rate-limit statistics in final pool diagnostics.

- [x] 12. Prefer secondary REST reset timing over the fallback (`src/ghbot/github/client.py`, `tests/unit/test_client.py`)
  - [x] 12.1 Add a focused failing client test for a secondary REST response without `Retry-After` whose rate headers report exhausted quota and a reset time.
  - [x] 12.2 Derive that secondary delay from the reset time, retaining the 60-second fallback when usable reset data is absent.

- [x] 13. Correct per-section combo completion and zero-wait policy (`src/ghbot/runner.py`, `src/ghbot/rate_limit.py`, `tests/unit/test_runner.py`, `tests/unit/test_rate_limit.py`)
  - [x] 13.1 Add focused failing tests proving a completed combo section remains complete when another section aborts, and that zero `max-rate-wait` rejects a zero-delay rate-limit signal.
  - [x] 13.2 Derive nested section outcomes from their per-mode ledgers and reject every rate-limit signal when the wait budget is zero.

- [x] 14. Correct accepted rate-limit resilience review findings (`src/ghbot/{executor.py,runner.py,rate_limit.py,report_style.py,__main__.py}`, `src/ghbot/github/client.py`, `tests/unit/{test_executor.py,test_runner.py,test_rate_limit.py,test_client.py,test_main.py,test_report_composition.py}`)
  - [x] 14.1 Add focused failing regression tests for fatal-abort grace/cancellation, GraphQL HTTP rate-limit classification, no retry after abort, explicit-selection ledger accuracy, non-rate network failures, fractional reset waits, TOML validation, and one combo text banner.
  - [x] 14.2 Implement the accepted corrections, retaining fractional-second internal delays and only targeted regression coverage.
