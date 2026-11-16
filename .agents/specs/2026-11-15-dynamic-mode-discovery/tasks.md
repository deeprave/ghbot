# Tasks: dynamic mode discovery

- [x] 1. Define and test trusted built-in mode discovery.
  - [x] 1.1 Add discovery tests for real definitions, canonical order, combinable filtering, and actionable invalid-candidate failures in `tests/unit/test_mode_discovery.py`.
  - [x] 1.2 Implement the runtime mode boundary, package enumeration, validation, ordering, and discovery error in `src/ghbot/modes/`.
- [x] 2. Make existing reportable modes expose the common discovery contract.
  - [x] 2.1 Extend focused mode/discovery tests to assert that security, issues, and drift supply their Click command and combinability metadata.
  - [x] 2.2 Attach the existing commands and combinability metadata to the `MODE` definitions in `src/ghbot/modes/security.py`, `issues.py`, and `drift.py` without altering their command behaviour.
- [x] 3. Move the non-reporting info command into a discovered mode.
  - [x] 3.1 Add a focused CLI/mode test that invokes discovered `info` and preserves its non-reporting runner path.
  - [x] 3.2 Add `src/ghbot/modes/info.py` with `InfoMode`, its Click command, and non-combinable metadata.
- [x] 4. Register commands dynamically from discovery.
  - [x] 4.1 Add or adapt CLI tests to prove all four commands are registered dynamically and retain their public help/options.
  - [x] 4.2 Replace static command imports and registration in `src/ghbot/__main__.py` with discovery registration; remove obsolete static registry wiring.
- [x] 5. Run focused regression coverage and reconcile spec tracking.
  - [x] 5.1 Run affected mode, runner, and CLI tests through `uv run`; resolve regressions without changing scan/report contracts.
