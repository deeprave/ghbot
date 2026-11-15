# Technology and Architecture

## Runtime and tools

- Python >= 3.13, packaged with `uv-build`.
- Run repository programs and developer tools through `uv run`.
- Manage dependencies with `uv add`; do not use `pip` or `uv pip install`.
- Lint with Ruff and type-check with ty.

## Architecture

- `src/ghbot/__main__.py` owns Click command parsing, configuration merge, and the synchronous to
  asynchronous entrypoint.
- `src/ghbot/github/` owns authentication, GitHub-client integration, and repository discovery.
- `src/ghbot/processor.py` defines repository processors, result records, and monitoring contracts.
- `src/ghbot/modes/` contains mode-specific processor and collection-report handlers.
- `src/ghbot/report_style.py` contains shared plain, table, and JSON rendering styles.
- `src/ghbot/executor.py` supplies bounded concurrent execution.

## Implementation conventions

- I/O and repository processing are async-first; do not introduce synchronous blocking work into
  the scan path.
- Use structural protocols where a boundary needs substitution or test doubles.
- Treat the merged configuration mapping as the source of truth; do not introduce parallel
  configuration channels.
- `FatalError` reaches the synchronous `main()` boundary; async processor code must not swallow it.
