# PR #44 review fixes

## Bug description

`ghbot.modes` binds package attributes named `drift`, `issues`, and `security` to Click commands,
shadowing the corresponding mode modules. The global-option rejection test can also pass because of
an unrelated runner failure.

## Reproduction

`from ghbot.modes import drift` returns a Click command, so `drift.MODE` raises `AttributeError`.
The shell test only asserts a non-zero exit for `ghbot --json info`.

## Expected and actual

Package mode imports remain modules, while `BUILTIN_COMMANDS` contains their explicit Click command
attributes. The shell test proves Click rejects `--json` before invoking the info runner.

## Root cause

Command imports in `ghbot.modes.__init__` reused the mode-module names. The shell test asserted a
generic error rather than its intended parse failure.

## Fix approach

Import mode modules in the package and build the command tuple from their command attributes.
Strengthen the existing shell test with a mocked runner and an unknown-option assertion.
