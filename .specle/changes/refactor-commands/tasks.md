# Tasks: Command-line command refactor

- [x] 1. Add focused failing CLI tests for the three leading `--schema` forms, exact-one selector
  validation, removed `schema` command, ungated selector rejection, and no processor activity.
  - Files: `tests/unit/test_schema_command.py`, `tests/unit/test_main.py`
- [x] 2. Implement the leading-only schema dispatcher and unregister the `schema` subcommand while
  preserving the existing schema selector and JSON output behaviour.
  - Reopened after review: use a private sentinel route rather than Click's private argument state.
  - Files: `src/ghbot/__main__.py`, `src/ghbot/schema.py`
- [x] 3. Add failing help-output tests for the root schema-retrieval guidance, scan-only command
  list, and exact `Scan for …` descriptions.
  - Files: `tests/unit/test_main.py`
- [x] 4. Standardise combo and mode descriptions, document the leading schema forms, and satisfy
  the help-output contract.
  - Files: `src/ghbot/combo.py`, `src/ghbot/modes/{info,drift,issues,security}.py`, `README.md`
