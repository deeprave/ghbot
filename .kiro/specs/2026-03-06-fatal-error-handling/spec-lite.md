# Spec Lite: Fatal Error Handling

## Problem
Fatal errors in async context must surface cleanly to the user with actionable messages and correct exit codes — no tracebacks, no `sys.exit()` from async code.

## Exception Hierarchy
```
FatalError(Exception)   message: str, exit_code: int
  └── AuthError         exit_code=1
```

## AuthError — Three Cases
1. `gh` not in PATH → `FileNotFoundError` → `AuthError` with platform install hint
2. `gh` exits non-zero → `CalledProcessError` → `AuthError` with `gh auth login` instruction
3. `gh` returns empty token → `AuthError` with `gh auth login` instruction

## Platform Install Hints (gh not found)
- Darwin: `brew install gh` or `port install gh`
- Linux: `sudo apt install gh`
- Windows: `winget install GitHub.cli` or `scoop install gh`
- Always append: https://cli.github.com

## Catch Pattern (main only)
```python
try:
    asyncio.run(_main(cfg))
except FatalError as e:
    log.error(e.message)
    sys.exit(e.exit_code)
```

## Rules
- `FatalError` never caught or swallowed in async code — always propagates to `main()`
- No `sys.exit()` / `SystemExit` outside `main()`
- No new dependencies — stdlib only

## Output Files
- `src/ghbot/errors.py`
- `src/ghbot/github/auth.py`
- `src/ghbot/__main__.py`
- `tests/unit/test_errors.py`
- `tests/unit/test_auth.py`
