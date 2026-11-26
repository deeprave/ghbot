# Implementation Tasks

- [x] 1. Define and test drift processor behavior (`tests/unit/test_drift_processor.py`, `src/ghbot/processor.py`)
  - [x] 1.1 Add failing async tests for stable-release lookup, default-branch compare, no-release skip, zero filtering, and rate-limit propagation.
  - [x] 1.2 Implement `DriftRepoProcessor` with the minimum result keys and API/error policy.
- [x] 2. Detect PyPI publishing configuration (`tests/unit/test_drift_processor.py`, `src/ghbot/processor.py`)
  - [x] 2.1 Add failing tests for workflow signals, no signal, and workflow-inspection failure.
  - [x] 2.2 Implement workflow tree/blob inspection and PyPI signal detection.
- [x] 3. Render drift reports (`tests/unit/test_drift_report.py`, `src/ghbot/report.py`)
  - [x] 3.1 Add failing tests for plain, table, and JSON filtering, summary, sorting, and unknown PyPI output.
  - [x] 3.2 Implement `render_drift_report()` and `print_drift_report()` in the shared report module.
- [x] 4. Wire the CLI (`tests/unit/test_main.py`, `src/ghbot/__main__.py`)
  - [x] 4.1 Add failing CLI tests for `drift`, its formats, and output handoff.
  - [x] 4.2 Implement the `drift` command and shared-report integration.
- [x] 5. Verify and record completion
  - [x] 5.1 Update the compact spec with implementation outcome.
  - [x] 5.2 Run `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
