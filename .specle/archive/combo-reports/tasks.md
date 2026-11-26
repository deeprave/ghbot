# Implementation Tasks: combo reports

- [x] 1. Add shared one-pass combo orchestration in `runner.py`.
  - [x] 1.1 Add focused async runner tests proving one discovery pass, one repository task,
    discovered-mode iteration, per-mode collection grouping, shared context/owner type, and fatal
    error propagation.
  - [x] 1.2 Implement `run_combo()` using `ReportableModeDefinition`, mode-keyed options, the
    existing auth/client/discovery/TaskPool path, and `CombinedCollectionReport`.
- [x] 2. Add the combo coordinator command and application registration.
  - [x] 2.1 Add command tests for format routing, `--labels` isolation, output forwarding,
    format-conflict rejection, fatal exits, and top-level CLI availability without scanner
    discovery of combo itself.
  - [x] 2.2 Implement `ghbot.combo` as the Click/FatalError boundary and register its command in
    `__main__.py` without adding a static scanner-mode registry.
- [x] 3. Confirm composition and discovery-derived output contracts.
  - [x] 3.1 Extend collection-composition tests for canonical section/key ordering and unchanged
    nested collection documents.
  - [x] 3.2 Reconcile any narrow report-composition or discovery integration needed to preserve
    the current drift/issues/security schemas and exclude info.
- [x] 4. Update user and contributor documentation.
  - [x] 4.1 Add the `combo` command, formats, labels behaviour, and one-pass scope to README.
  - [x] 4.2 Explain the coordinator-versus-discoverable-mode boundary in CONTRIBUTING.
- [x] 5. Close verification coverage gaps for combo behaviour.
  - [x] 5.1 Add runner coverage for fatal processor propagation and retaining other mode results
    when one result is partial.
  - [x] 5.2 Add plain combined-output coverage for labelled canonical-order sections.
- [x] 6. Prevent duplicate collection entries when a repository task retries.
  - [x] 6.1 Add a regression test using the real `TaskPool` secondary-rate-limit retry path.
  - [x] 6.2 Stage a repository's mode results and add them only after every mode completes.
- [x] 7. Preserve fatal processor errors through shared task execution.
  - [x] 7.1 Add a real-`TaskPool` regression test for a non-rate-limit `FatalError` preserving its
    message and exit code.
  - [x] 7.2 Retain and re-raise that fatal error from `TaskPool` after in-flight work completes.
- [x] 8. Deduplicate configured owner scans deterministically.
  - [x] 8.1 Add CLI/config tests for case-insensitive duplicate owners, first-seen ordering, and
    duplicate logging before bare repository expansion.
  - [x] 8.2 Normalise owners once in the application shell before scanner invocation.
- [x] 9. Preserve fatal errors raised during a secondary-limit retry.
  - [x] 9.1 Add a regression test for a secondary-limit first attempt followed by a non-rate-limit
    `FatalError`, asserting that the original error reaches the caller.
  - [x] 9.2 Route retry-path fatal errors through the same preservation path as initial attempts.

- [x] 10. Replace the boolean combination flag with ordered keys (`tests/unit/test_mode_discovery.py`, `src/ghbot/modes/_discovery.py`, `src/ghbot/modes/security.py`, `src/ghbot/modes/issues.py`, `src/ghbot/modes/drift.py`, `src/ghbot/modes/info.py`, `tests/unit/test_combo.py`, `CONTRIBUTING.md`)
  - [x] 10.1 Add failing discovery and combo-output tests for the security `010`, issues `020`, drift `030` order, unkeyed info exclusion, malformed or duplicate keys, and unchanged alphabetical command discovery.
  - [x] 10.2 Replace `combinable` with optional `combine_key`, validate unique zero-padded keys for reportable modes, and make `combinable_modes()` select and order keyed modes.
  - [x] 10.3 Assign the initial keys, update contributor guidance, and preserve all existing coordinator, retry, fatal-error, labels, and standalone-command behaviour.

- [x] 11. Retain completed mode results after an ordinary later-mode failure.
  - [x] 11.1 Add a real-`TaskPool` regression test where a later mode raises an ordinary exception and assert that earlier completed-mode results are retained.
  - [x] 11.2 Retain completed results across retry attempts, skip already-completed modes on retry, and commit only the appropriate successful results without changing fatal or rate-limit propagation.
