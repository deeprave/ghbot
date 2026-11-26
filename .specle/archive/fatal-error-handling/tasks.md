# Tasks: Fatal Error Handling

## Task 1: Define FatalError and AuthError in errors.py
- [x] Create `src/ghbot/errors.py` with `FatalError(Exception)` (message, exit_code) and `AuthError(FatalError)` (exit_code=1)

## Task 2: Write tests for errors.py
- [x] Create `tests/unit/test_errors.py` covering FatalError attributes and AuthError subclass/exit_code

## Task 3: Update get_auth_token() to raise AuthError
- [x] Update `src/ghbot/github/auth.py` to catch FileNotFoundError, CalledProcessError, and empty token — raise AuthError with platform-aware messages

## Task 4: Write tests for auth.py
- [x] Create `tests/unit/test_auth.py` covering all three AuthError cases and platform hint logic

## Task 5: Update main() to catch FatalError
- [x] Update `src/ghbot/__main__.py` to catch FatalError, log message, and sys.exit(e.exit_code)
