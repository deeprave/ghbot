# Requirements Document

## Introduction

ghbot's JSON reports have no version identifier or shipped schema. Consumers cannot distinguish a compatible additive change from an incompatible document. The security, issues, drift, and combined report documents need an explicit, package-distributed contract.

## Glossary

- **report document**: The JSON object returned by a report collection's `document()` method and emitted by `--json`.
- **schema version**: A `MAJOR.MINOR` string declaring the report document contract.
- **mode**: The report identity: `security`, `issues`, `drift`, or `combined`.
- **combined wrapper**: The top-level document that nests the standalone report documents.

## Requirements

### Requirement 1: Identify every JSON report document

**User Story:** As a consumer, I want each JSON document to declare its type and version so that I can reject incompatible input safely.

#### Acceptance Criteria

1. THE JSON document for each reportable mode SHALL include top-level `schema_version` and `mode` keys.
2. THE initial schema version for each standalone mode and the combined wrapper SHALL be `1.0`.
3. THE mode values SHALL be `security`, `issues`, `drift`, and `combined` as applicable.
4. THE combined wrapper SHALL include its own version and mode and SHALL retain each nested mode document with that mode's own version and mode.
5. The collection `document()` methods SHALL return the same versioned shape that their `--json` commands emit.

### Requirement 2: Ship machine-readable schemas

**User Story:** As a consumer and library user, I want schemas available from the installed package so that I can validate report documents.

#### Acceptance Criteria

1. THE package SHALL ship one JSON Schema file for every standalone report mode and the combined wrapper.
2. Each schema file SHALL be accessible through `importlib.resources` after wheel and source-distribution installation.
3. Schemas SHALL describe `null` as an unavailable value wherever the current report contract permits it.
4. Schemas SHALL permit additional properties so a consumer that supports a schema minor version remains compatible with later additive fields.

### Requirement 3: Publish compatibility policy and prevent drift

**User Story:** As an integrator, I want clear versioning rules and validated output so that upgrades are predictable.

#### Acceptance Criteria

1. README documentation SHALL state that optional additive fields increment MINOR, while removals, renames, type changes, or semantic changes increment MAJOR.
2. README documentation SHALL advise consumers to reject unsupported MAJOR versions.
3. Tests SHALL validate representative current, partial, and unavailable output for every schema-backed document against its shipped schema.
4. Tests SHALL fail when a document no longer conforms to its declared schema.

## Non-Functional Requirements

- The initial schemas SHALL describe the report contracts implemented at delivery time; later additive fields follow the documented minor-version policy.
- Preserve plain and table output behaviour.
- Package schema assets in both wheel and sdist.
- Run all project checks through `uv run` when implementation begins.
