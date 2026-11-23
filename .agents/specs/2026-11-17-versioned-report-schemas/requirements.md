# Requirements Document

## Introduction

ghbot's JSON reports have no shipped, versioned schema contract. Consumers need schemas that
describe the actual report documents and a package-distributed registry to resolve them. JSON
Schema `$id` identifies a schema resource, not an instance, so schema selection must be external to
the report payload.

## Glossary

- **report document**: The JSON object returned by a report collection's `document()` method and emitted by `--json`.
- **schema identifier**: The canonical `ghbot:` `$id` of a versioned JSON Schema resource. Initial identifiers use `ghbot://schemas/<report>/1.0.json`.
- **schema registry**: The public ghbot library interface that resolves canonical schema identifiers and report identities to their packaged JSON Schema resources.
- **report identity**: The report type: `security`, `issues`, `drift`, or `combined`.
- **combined wrapper**: The top-level document that nests the standalone report documents.

## Requirements

### Requirement 1: Identify schema resources without changing report payloads

**User Story:** As a consumer, I want stable canonical identities for report schemas while keeping
report payloads compatible with established JSON Schema conventions.

#### Acceptance Criteria

1. THE initial standalone schema identifiers SHALL be `ghbot://schemas/security/1.0.json`, `ghbot://schemas/issues/1.0.json`, and `ghbot://schemas/drift/1.0.json`; the combined schema identifier SHALL be `ghbot://schemas/combined/1.0.json`.
2. EACH schema resource SHALL declare its own canonical `$id`.
3. JSON report documents SHALL preserve their pre-schema shape and SHALL NOT add `$id` or another schema-identification property.
4. The combined document SHALL retain the established nested standalone-report shapes without adding schema-identification properties.

### Requirement 2: Ship machine-readable schemas

**User Story:** As a consumer and library user, I want a public registry for installed schema resources so that I can resolve and validate report documents without depending on package-file paths.

#### Acceptance Criteria

1. THE package SHALL ship one versioned JSON Schema resource for every standalone report identity and the combined wrapper.
2. THE public schema registry SHALL resolve a schema by canonical `ghbot:` `$id`, discover the current schema for a report identity, and expose the packaged schema document without callers depending on package-file paths or URI-scheme dereferencing.
3. Registry-backed schemas SHALL remain accessible after wheel and source-distribution installation.
4. Schemas SHALL describe every currently emitted summary, repository, item, and nested-detail field, including `null` wherever the current report contract permits it.
5. Schemas SHALL permit additional properties so a consumer that supports a schema minor version remains compatible with later additive fields.
6. The registry SHALL expose the current packaged schema identifiers through `schema_ids()` so consumers can preload resources for local combined-schema validation without hardcoding identifiers.
7. Unknown report identities and schema identifiers SHALL raise `ValueError`; missing, unreadable, malformed, non-object, or mismatched packaged schema resources SHALL raise a distinct local package-data error that includes the requested schema identifier.

### Requirement 3: Publish compatibility policy and prevent drift

**User Story:** As an integrator, I want clear versioning rules and validated output so that upgrades are predictable.

#### Acceptance Criteria

1. README documentation SHALL state that optional additive fields increment the MINOR component of a schema `$id`, while removals, renames, type changes, or semantic changes increment its MAJOR component.
2. README documentation SHALL advise consumers to resolve schemas by report identity or canonical schema ID through the registry and reject unsupported MAJOR versions.
3. Tests SHALL validate representative real current, partial, and unavailable output from every report collection against the schema resolved by that collection's report identity.
4. Tests SHALL fail when a real report document does not conform to the schema selected for its report identity.
5. Distribution tests SHALL execute registry lookups from both the built wheel and source distribution with the checkout excluded from import resolution.
6. Documentation SHALL show consumers how to preload packaged resources for combined-schema validation without network dereferencing.

## Non-Functional Requirements

- The initial schemas SHALL describe the report contracts implemented at delivery time; later additive fields follow the documented schema-identifier version policy.
- Preserve plain and table output behaviour.
- Package schema assets in both wheel and sdist.
- Preserve security repository metric semantics: absent means an unexpected failed scan produced no metric, `null` means a metric was attempted but unavailable, and `0` means it was successfully fetched with no findings.
- Run all project checks through `uv run` when implementation begins.
