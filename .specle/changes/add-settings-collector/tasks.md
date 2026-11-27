# Tasks: Settings collector

- [x] 1. Add focused client tests for GraphQL responses containing both usable data and field
  errors, plus no-data, forbidden, and rate-limit precedence.
  - Files: `tests/unit/test_client.py`, `src/ghbot/errors.py`, `src/ghbot/github/client.py`
- [x] 2. Implement the typed partial-GraphQL condition and preserve existing fatal and no-data
  error translation.
  - Files: `src/ghbot/errors.py`, `src/ghbot/github/client.py`, `src/ghbot/processor.py`
- [x] 3. Add settings-processor tests for curated core projection, default-branch classic
  protection, rulesets, and bypass-presence-only output.
  - Files: `tests/unit/test_settings_processor.py`, `src/ghbot/modes/settings.py`
- [x] 4. Implement the single core GraphQL query and safe settings projection, including
  field-error-to-section availability mapping and partial-result status.
  - Files: `src/ghbot/modes/settings.py`, `src/ghbot/processor.py`
- [x] 5. Add tests for paginated Actions variable and secret names, fetched-empty lists, endpoint
  failures, and value redaction.
  - Files: `tests/unit/test_settings_processor.py`, `tests/unit/test_processor.py`
- [x] 6. Implement Actions name-only REST listings using keyed pagination and independent
  unavailable metadata, including failure when no reportable settings section exists.
  - Files: `src/ghbot/processor.py`, `src/ghbot/modes/settings.py`
- [x] 7. Add issues-mode tests for a usable partial GraphQL pull-request connection and an
  unusable partial connection.
  - Files: `tests/unit/test_issues_processor.py`, `src/ghbot/modes/issues.py`
- [x] 8. Adopt the partial-GraphQL condition in issues-mode pull-request processing without
  changing its existing unavailable-metric semantics.
  - Files: `src/ghbot/modes/issues.py`
- [x] 9. Add report, CLI, discovery, output-file, and schema tests for the standalone settings
  mode, including rejection of table output and exclusion from combo.
  - Files: `tests/unit/test_settings_report.py`, `tests/unit/test_settings_report_mode.py`,
    `tests/unit/test_main.py`, `tests/unit/test_schemas.py`
- [x] 10. Implement settings collection rendering, standalone mode wiring, packaged schema
  registration, and concise README documentation.
  - Files: `src/ghbot/modes/settings.py`, `src/ghbot/schemas/settings/1.0.json`,
    `src/ghbot/schemas/__init__.py`, `README.md`
- [x] 11. Run the full quality gates and validate settings JSON documents against their packaged
  schema.
  - Files: `tests/integration/test_schema_distribution.py`, `tests/unit/test_schemas.py`
- [x] 12. Preserve readable rulesets when GitHub denies only bypass-actor presence, omitting the
  unavailable `bypass_actors` property and recording its availability separately.
  - Files: `tests/unit/test_settings_processor.py`, `tests/unit/test_report_schemas.py`,
    `src/ghbot/modes/settings.py`, `src/ghbot/schemas/settings/1.0.json`
