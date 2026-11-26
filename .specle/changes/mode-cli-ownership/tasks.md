# Implementation Tasks

- [x] 1. Extract the dependency-neutral scan runner (`src/ghbot/runner.py`, `src/ghbot/__main__.py`, `tests/unit/test_runner.py`)
  - [x] 1.1 Add failing runner tests for processor construction, owner-type propagation, TaskPool collection timing, authentication, discovery, and fatal-error propagation.
  - [x] 1.2 Move `_main()` and `_run_mode()` into `runner.py` as CLI-format-agnostic async functions; retain the `info` path's behaviour through the extracted processor runner.

- [x] 2. Give the security mode its Click command (`src/ghbot/modes/security.py`, `tests/unit/test_security_report_mode.py`)
  - [x] 2.1 Add failing command tests for security help, default/plain/table/JSON option mapping, mutually exclusive format failures, output forwarding, and `FatalError` exit handling.
  - [x] 2.2 Implement the security command with its format/output options, mode-runner invocation, collection rendering, and shared writer call.

- [x] 3. Give the issues mode its Click command (`src/ghbot/modes/issues.py`, `tests/unit/test_issues_report_mode.py`)
  - [x] 3.1 Add failing command tests for issues format/output routing, `--labels` routing with each format, mutually exclusive format failures, and `FatalError` exit handling.
  - [x] 3.2 Implement the issues command with its format, labels, and output options, mode-runner invocation, collection rendering, and shared writer call.

- [x] 4. Give the drift mode its Click command (`src/ghbot/modes/drift.py`, `tests/unit/test_drift_report_mode.py`)
  - [x] 4.1 Add failing command tests for drift help, default/plain/table/JSON option mapping, mutually exclusive format failures, output forwarding, and `FatalError` exit handling.
  - [x] 4.2 Implement the drift command with its format/output options, mode-runner invocation, collection rendering, and shared writer call.

- [x] 5. Register mode-owned commands through the package boundary (`src/ghbot/modes/__init__.py`, `src/ghbot/__main__.py`, `tests/unit/test_main.py`)
  - [x] 5.1 Add failing shell tests that the package-provided commands are registered, global options apply before each registered mode, and mode-specific options are absent from `__main__.py`.
  - [x] 5.2 Export ordered `BUILTIN_COMMANDS`, register it with the application group, and remove report-mode flags, option mappings, direct mode imports, rendering, and runner ownership from the shell.
