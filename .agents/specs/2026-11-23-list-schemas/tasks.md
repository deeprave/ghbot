# Fix Tasks: list schema names and IDs

- [x] 1. Add schema discovery to the local registry and CLI (`src/ghbot/schemas/__init__.py`, `src/ghbot/schema.py`, `tests/unit/test_schemas.py`, `tests/unit/test_schema_command.py`)
  - [x] 1.1 Write a failing regression test for `ghbot schema --list`, selector conflicts, registry-backed name/ID entries, and local-only behavior.
  - [x] 1.2 Implement the smallest registry enumeration API and `--list` path without changing existing retrieval forms.

- [x] 2. Document schema discovery (`README.md`)
  - [x] 2.1 Add the `ghbot schema --list` invocation and its name/ID JSON output to the existing schema CLI documentation.
