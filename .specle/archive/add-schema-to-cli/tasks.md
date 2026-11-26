# Implementation Tasks: add schema to CLI

- [x] 1. Add the local schema command and register it with the root CLI (`src/ghbot/schema.py`, `src/ghbot/__main__.py`, `tests/unit/test_schema_command.py`, `tests/unit/test_main.py`)
  - [x] 1.1 Cover report-identity and canonical-ID lookups, valid newline-terminated JSON, selector validation, unsupported-selector usage errors, and the absence of authentication, scanning, and network activity.
  - [x] 1.2 Implement the Click command using only `current_schema()` and `schema_for_id()`, then register it without changing existing commands.

- [x] 2. Document packaged schema retrieval for CLI users (`README.md`)
  - [x] 2.1 Add both `ghbot schema <report>` and `ghbot schema --id <canonical-schema-id>` forms, including their installed-package and no-network behaviour.
