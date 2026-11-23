# Implementation Tasks: versioned report schemas

## Active revision tasks (2026-11-23)

## Accepted review correction tasks (2026-11-23)

- [x] 1. Harden the public schema registry (`src/ghbot/schemas/__init__.py`, `tests/unit/test_schemas.py`)
  - [x] 1.1 Add `schema_ids()` and `SchemaPackageError`, distinguish package-data failures from unknown caller IDs, and verify resource `$id` integrity.
  - [x] 1.2 Test malformed, unreadable, non-object, and mismatched package resources without conflating them with `ValueError`.

- [x] 2. Make built-artifact validation genuinely isolated (`tests/integration/test_schema_distribution.py`)
  - [x] 2.1 Execute the registry check against both wheel and sdist outside the checkout using the test interpreter and `--no-project`.

- [x] 3. Complete combined and contract validation coverage (`tests/unit/test_report_schemas.py`, report-mode tests)
  - [x] 3.1 Use registry resources discovered through `schema_ids()` for populated, partial, and nested-invalid combined documents.
  - [x] 3.2 Add focused meta-schema, additive-property, rendered-JSON parity, nullable, and nested-negative tests.

- [x] 4. Document schema loading and security metric states (`README.md`, `src/ghbot/schemas/security/1.0.json`)
  - [x] 4.1 Document local combined-schema preloading and absent/`null`/zero security metric semantics.

- [x] 5. Restore maintainable contract presentation (`src/ghbot/report_style.py`, `src/ghbot/schemas/*/1.0.json`)
  - [x] 5.1 Remove redundant combined-document unpacking and pretty-print all schema resources.

- [x] 1. Remove schema identifiers from emitted report documents (`tests/unit/test_security_report.py`, `tests/unit/test_issues_report.py`, `tests/unit/test_drift_report.py`, `src/ghbot/modes/security.py`, `src/ghbot/modes/issues.py`, `src/ghbot/modes/drift.py`)
  - [x] 1.1 Add failing regression tests for the established standalone JSON shapes, explicitly excluding `$id` or any schema-identification property.
  - [x] 1.2 Remove report-registry lookups from the standalone collection `document()` methods while retaining unchanged plain, table, and JSON rendering.

- [x] 2. Restore the established combined document shape (`tests/unit/test_report_composition.py`, `tests/unit/test_combo.py`, `src/ghbot/report_style.py`, `src/ghbot/schemas/combined/1.0.json`)
  - [x] 2.1 Add failing composition and command tests proving the wrapper has only its report sections and each nested document has its established standalone shape.
  - [x] 2.2 Remove the wrapper schema property from `CombinedCollectionReport.document()` and update the combined schema to validate the identifier-free wrapper through local external `$ref` values.

- [x] 3. Complete standalone schema contracts from real report output (`tests/unit/test_report_schemas.py`, `src/ghbot/schemas/security/1.0.json`, `src/ghbot/schemas/issues/1.0.json`, `src/ghbot/schemas/drift/1.0.json`)
  - [x] 3.1 Add failing validation tests using real complete, partial, and unavailable documents from every collection, selected with `current_schema(report)`.
  - [x] 3.2 Model every current summary, repository, item, metric, and detail field with its actual type and nullable-unavailable semantics, while retaining additive-property compatibility.

- [x] 4. Prove report-identity-based validation and local reference resolution (`tests/unit/test_report_schemas.py`, `tests/unit/test_schemas.py`)
  - [x] 4.1 Add negative tests that mutate actual collection output into required-field and type violations, proving validation fails against the identity-selected schema.
  - [x] 4.2 Validate real combined output with the four packaged resources preloaded, proving external `$ref` values resolve without network access.

- [x] 5. Correct public documentation and packaging coverage (`README.md`, `tests/integration/test_schema_distribution.py`)
  - [x] 5.1 Update README to distinguish schema-resource `$id` from report instances and document registry lookup by report identity or canonical ID.
  - [x] 5.2 Retain and extend built-artifact checks so installed wheel and source distributions expose every schema resource through the public registry.

## Superseded task record (2026-11-22)

The completed tasks below produced the registry and packaged resources, but their payload-`$id`
outcomes are reopened above because they conflict with the revised JSON Schema contract.

- [x] 1. Add the package-local schema registry (`tests/unit/test_schemas.py`, `src/ghbot/schemas/__init__.py`)
  - [x] 1.1 Write failing registry tests for the four current report identities, their exact `ghbot:` IDs, ID-based resolution, fresh returned documents, unsupported identities/IDs, and package-data failures without network access.
  - [x] 1.2 Implement `current_schema_id()`, `current_schema()`, and `schema_for_id()` with an explicit identity/ID-to-resource map and `importlib.resources` loading.

- [x] 2. Define the standalone versioned resources (`tests/unit/test_report_schemas.py`, `pyproject.toml`, `uv.lock`, `src/ghbot/schemas/security/1.0.json`, `src/ghbot/schemas/issues/1.0.json`, `src/ghbot/schemas/drift/1.0.json`)
  - [x] 2.1 Add `jsonschema` as a development-only dependency and write failing Draft 2020-12 validation tests for representative current, partial, and unavailable security, issues, and drift documents resolved through each document's emitted `$id`.
  - [x] 2.2 Add the three self-identifying schemas with constant instance `$id` properties, current summary/repository contracts, applicable nullable values, optional issue labels, and permissive additional properties.

- [x] 3. Identify security JSON reports (`tests/unit/test_security_report.py`, `tests/unit/test_security_report_mode.py`, `src/ghbot/modes/security.py`)
  - [x] 3.1 Add failing collection and `--json` rendering tests asserting the security document carries `ghbot://schemas/security/1.0.json` while plain and table output stay unchanged.
  - [x] 3.2 Add the security schema ID at the `SecurityCollectionReport.document()` boundary so direct documents and rendered JSON share one mapping.

- [x] 4. Identify issues JSON reports (`tests/unit/test_issues_report.py`, `tests/unit/test_issues_report_mode.py`, `src/ghbot/modes/issues.py`)
  - [x] 4.1 Add failing collection and `--json` rendering tests asserting the issues document carries `ghbot://schemas/issues/1.0.json`, including labels-present, partial, and unavailable metric cases without changing plain/table output.
  - [x] 4.2 Add the issues schema ID at the `IssuesCollectionReport.document()` boundary.

- [x] 5. Identify drift JSON reports (`tests/unit/test_drift_report.py`, `tests/unit/test_drift_report_mode.py`, `src/ghbot/modes/drift.py`)
  - [x] 5.1 Add failing collection and `--json` rendering tests asserting the drift document carries `ghbot://schemas/drift/1.0.json`, including unavailable PyPI configuration without changing plain/table output.
  - [x] 5.2 Add the drift schema ID at the `DriftCollectionReport.document()` boundary.

- [x] 6. Identify and validate combined JSON reports (`tests/unit/test_report_composition.py`, `tests/unit/test_combo.py`, `tests/unit/test_report_schemas.py`, `src/ghbot/report_style.py`, `src/ghbot/schemas/combined/1.0.json`)
  - [x] 6.1 Add failing composition and command tests asserting the wrapper emits `ghbot://schemas/combined/1.0.json` and retains the independently identified nested documents.
  - [x] 6.2 Add the combined schema with local-registry `$ref` values for the three standalone schemas; extend validation tests to preload all package resources, validate the combined document through its emitted ID, and reject mismatched IDs and contract violations.
  - [x] 6.3 Add the wrapper schema ID in `CombinedCollectionReport.document()` without changing its plain/table section composition.

- [x] 7. Prove distribution access and document the compatibility contract (`tests/integration/test_schema_distribution.py`, `README.md`)
  - [x] 7.1 Add a failing built-artifact test that creates wheel and source-distribution artifacts in a temporary directory, installs or executes each artifact in isolation, and resolves every schema through the public registry without checkout paths.
  - [x] 7.2 Ensure the schema package resources are included by the build and update README with the registry API, initial `ghbot:` IDs, additive-minor/breaking-major policy, and unsupported-major handling.
