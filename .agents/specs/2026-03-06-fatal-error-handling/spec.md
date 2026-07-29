# Spec: Fatal Error Handling

## Problem / Context

ghbot is an async CLI app. Fatal errors (auth failures, missing tools, bad config) can occur
in async context but must be communicated clearly to the user and exit cleanly with a meaningful
code — without calling `sys.exit()` or raising `SystemExit` from within the async layer.

The first concrete case is authentication: ghbot delegates auth to the GitHub CLI (`gh`).
If `gh` is missing, unauthenticated, or returns an empty token, the app cannot proceed.
Users need actionable guidance, not a traceback.

---

## Requirements

### Functional

1. A `FatalError` base exception class exists in `src/ghbot/errors.py`
2. `FatalError` carries a user-facing `message: str` and an `exit_code: int`
3. Subclasses exist for distinct fatal categories:
   - `AuthError(FatalError)` — authentication failures (exit code 1)
   - Additional subclasses added as new fatal categories are identified
4. `get_auth_token()` raises `AuthError` for all three failure cases:
   - `gh` not found / not in PATH → `FileNotFoundError` mapped to `AuthError`
   - `gh` exits non-zero (not authenticated) → `CalledProcessError` mapped to `AuthError`
   - `gh` exits 0 but returns empty token → `AuthError`
5. `AuthError` messages are platform-aware:
   - **not found**: includes platform-appropriate install instructions + fallback URL
   - **not authenticated**: instructs user to run `gh auth login`
6. `FatalError` is caught exclusively in the sync `main()` — never swallowed in async code
7. On catch: log the message at `error` level, then `sys.exit(e.exit_code)`

### Non-functional

- No `sys.exit()`, `os._exit()`, or `SystemExit` raised anywhere in async code
- No tracebacks shown to the user for fatal errors (unless `--verbose`)
- Error messages are plain English, actionable, and include next steps

---

## Constraints

- Python 3.11+ stdlib only for error handling — no new dependencies
- Platform detection via `platform.system()` — values: `Darwin`, `Linux`, `Windows`
- `get_auth_token()` is sync (subprocess call) — mapping exceptions is straightforward
- Must not break the existing lazy-cache pattern in `auth.py`

---

## High-level Design

```
src/ghbot/
├── errors.py          # FatalError, AuthError (and future subclasses)
└── github/
    └── auth.py        # get_auth_token() — raises AuthError on failure
```

### Exception hierarchy
```
FatalError(Exception)
  exit_code: int
  message: str
  └── AuthError        exit_code=1
```

### Platform-aware install hint (AuthError — gh not found)
| Platform | Primary hint | Secondary hint |
|----------|-------------|----------------|
| Darwin   | `brew install gh` or `port install gh` | https://cli.github.com |
| Linux    | `sudo apt install gh` (or distro equivalent) | https://cli.github.com |
| Windows  | `winget install GitHub.cli` or `scoop install gh` | https://cli.github.com |

### main() catch block
```python
try:
    asyncio.run(_main(cfg))
except FatalError as e:
    log.error(e.message)
    sys.exit(e.exit_code)
```

---

## Acceptance Criteria

- [ ] `FatalError` and `AuthError` defined in `src/ghbot/errors.py`
- [ ] `get_auth_token()` raises `AuthError` for all three failure cases
- [ ] `AuthError` message for missing `gh` includes platform-correct install hint
- [ ] `AuthError` message for unauthenticated `gh` includes `gh auth login` instruction
- [ ] `main()` catches `FatalError`, logs message, exits with `e.exit_code`
- [ ] No `sys.exit` / `SystemExit` outside of `main()`
- [ ] Unit tests cover all three `AuthError` cases and the platform hint logic

---

## Contract

```json
{
  "output_files": [
    "src/ghbot/errors.py",
    "src/ghbot/github/auth.py",
    "src/ghbot/__main__.py",
    "tests/unit/test_errors.py",
    "tests/unit/test_auth.py"
  ],
  "checks": [
    "FatalError has message and exit_code attributes",
    "AuthError is a subclass of FatalError with exit_code=1",
    "get_auth_token raises AuthError when gh not found",
    "get_auth_token raises AuthError when gh exits non-zero",
    "get_auth_token raises AuthError when gh returns empty string",
    "AuthError message for missing gh contains platform install hint",
    "main() catches FatalError and calls sys.exit(e.exit_code)",
    "no sys.exit outside of main()"
  ]
}
```
