# Project Testing and Quality Gates

## Test conventions

- Unit tests live in `tests/unit/`; integration tests belong in `tests/integration/` when needed.
- Async tests use `@pytest.mark.anyio`; the test backend is configured by `anyio_backend` in
  `tests/conftest.py`.
- Use `AsyncMock` for async calls and patch at the import site.
- Keep error-message assertions to useful substrings rather than exact wording.
- Property tests use Hypothesis when a universal behavioural invariant is valuable. Use
  `@settings(max_examples=100)` and place them beside the affected unit tests.

## Required verification gates

Run all gates through `uv run`:

```bash
uv run pytest -v -Werror -Walways
uv run ruff check
uv run ty check src/
uv run ruff format --check
```

Warnings are errors for pytest. Do not claim a clean test pass before the test command exits
successfully.
