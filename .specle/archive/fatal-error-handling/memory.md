# Memory: Fatal Error Handling

## Key Decisions

- `FatalError` carries both `message` and `exit_code` as explicit attributes (not just the `args` tuple) so callers can reference them by name without string parsing.
- `AuthError` hardcodes `exit_code=1` in its `__init__` — subclasses own their exit codes, callers don't set them.
- `sys.exit()` lives exclusively in the sync `main()` catch block. Async code raises; sync boundary exits.
- Platform install hints are a plain `dict` keyed on `platform.system()` return values (`Darwin`, `Linux`, `Windows`) with a `.get()` fallback — no if/elif chain.
- `get_auth_token()` stays sync (subprocess) — no async complexity needed, and the lazy-cache global `_token` pattern is preserved unchanged.

## Patterns Used

- **Async boundary error propagation**: fatal exceptions raised anywhere in async code propagate naturally to `asyncio.run()`, which re-raises them into the sync `main()` catch block. No special async machinery needed.
- **Lazy global cache with reset fixture**: `_token` global in `auth.py` requires an `autouse` pytest fixture to reset it before/after each test to prevent state leakage between tests.
- **Exception mapping at the source**: `FileNotFoundError` and `CalledProcessError` are caught immediately in `get_auth_token()` and re-raised as domain exceptions (`AuthError`). Nothing upstream needs to know about subprocess internals.
- **Platform hint dict with fallback**: `_INSTALL_HINTS.get(platform.system(), "see https://cli.github.com")` handles unknown platforms gracefully without branching.

## Lessons Learned

- Testing `main()` FatalError handling is cleanest via `click.testing.CliRunner` + `AsyncMock(side_effect=FatalError(...))` — no subprocess or real async work needed.
- The `autouse` reset fixture pattern for module-level globals is necessary any time a cached singleton is tested across multiple test functions.
- Keeping error message assertions loose (substring checks like `"gh auth login" in message`) makes tests resilient to wording changes while still verifying the actionable content.
- `FatalError.message` duplicates `str(e)` / `e.args[0]` but the explicit attribute is worth it for readability at the catch site (`log.error(e.message)` vs `log.error(str(e))`).

## Follow-ups

- Add `ConfigError(FatalError)` when config validation is implemented (exit code 2 suggested).
- Add `ToolError(FatalError)` for missing external tools beyond `gh` (e.g. `git`) — the platform hint dict pattern in `auth.py` is directly reusable.
- Consider a `--verbose` traceback: the spec mentions tracebacks should be suppressed unless `--verbose`, but the current `main()` catch block always suppresses. This needs wiring when `--verbose` is plumbed through.
- Linux install hint is Debian/Ubuntu-centric (`apt`) — could be improved with a note about other distros or a link only, but deferred until there's user feedback.
