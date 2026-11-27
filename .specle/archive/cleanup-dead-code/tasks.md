# Tasks: Clean up dead code

## Task 1: Preserve the live contracts while preparing removal

- [x] 1.1 Run the focused discovery, runner, and processor tests that establish the live
  `new_processor`, `options`, and explicit-repository contracts. Files: `tests/unit/test_mode_discovery.py`,
  `tests/unit/test_runner.py`, mode processor tests.
- [x] 1.2 Confirm the Vulture whitelist is limited to the runtime-checkable processor protocol,
  TRACE logger extension, and framework-signature names. Files: `vulture_whitelist.py`,
  `pyproject.toml`.

## Task 2: Remove unreferenced state and implementation

- [x] 2.1 Remove the unraised and uncaught `UnexpectedError` plus its self-referential test.
  Files: `src/ghbot/errors.py`, `tests/unit/test_errors.py`.
- [x] 2.2 Remove unused processor option snapshots while retaining the factory-compatible
  constructor parameter and explicitly discarding it. Files: `src/ghbot/processor.py`,
  `src/ghbot/modes/{drift,issues,security}.py`.
- [x] 2.3 Remove mode `processor_type` fields and their implementation-detail assertions. Files:
  `src/ghbot/modes/{drift,info,issues,security}.py`, corresponding report-mode tests.
- [x] 2.4 Remove the runner's unconsumed GitHub-client attribute assignment. File:
  `src/ghbot/runner.py`.

## Task 3: Prove the dead-code gate remains narrow and effective

- [x] 3.1 Run Vulture across all configured files and address only residual, evidence-backed
  findings. Files: Vulture configuration and whitelist only if required.
- [x] 3.2 Run the focused tests and all required quality gates. Files: affected source and tests.

## Task 4: Narrow signature suppression after review

- [x] 4.1 Rename safely-renamable unused framework and protocol parameters with underscore
  prefixes, retaining the required `url_vars` keyword-only protocol name. Files:
  `src/ghbot/__main__.py`, `src/ghbot/executor.py`, `src/ghbot/report_style.py`,
  `src/ghbot/processor.py`.
- [x] 4.2 Restrict Vulture `ignore_names` to `url_vars`, then rerun Vulture and the affected
  quality gates. File: `pyproject.toml`.
