# Requirements Document

## Introduction

ghbot ships versioned JSON Schema resources through its public Python registry, but CLI users and
shell automation cannot retrieve a schema without writing Python. A read-only schema command will
make the installed resources discoverable without embedding schema identifiers in report payloads
or dereferencing the custom `ghbot:` URI.

## Glossary

- **report identity**: One of `security`, `issues`, `drift`, or `combined`.
- **canonical schema ID**: The versioned `ghbot:` identifier declared by a shipped schema resource.
- **schema command**: The new `ghbot schema` CLI command that prints one packaged schema document.

## Requirements

### Requirement 1: Retrieve the current schema by report identity

**User Story:** As a CLI user, I want to request a schema by report identity so that I can inspect
or validate the current contract without knowing its versioned ID.

#### Acceptance Criteria

1. THE CLI SHALL provide `ghbot schema <report>` for each supported report identity.
2. THE command SHALL resolve the current schema through the public `ghbot.schemas` registry and
   write the complete schema document as valid, newline-terminated JSON to stdout.
3. THE command SHALL not authenticate, scan repositories, or make a network request.

### Requirement 2: Retrieve a schema by canonical ID

**User Story:** As an integrator, I want to request an exact schema ID so that automation can
retrieve the same version it encountered elsewhere.

#### Acceptance Criteria

1. THE CLI SHALL provide `ghbot schema --id <canonical-schema-id>`.
2. THE command SHALL resolve the exact packaged schema through `ghbot.schemas.schema_for_id()`
   and write the complete schema document as valid, newline-terminated JSON to stdout.
3. THE positional report identity and `--id` SHALL be mutually exclusive, and the command SHALL
   require exactly one selection method.

### Requirement 3: Give useful local errors and documentation

**User Story:** As a CLI user, I want invalid schema requests to fail clearly so that I can correct
them without guessing whether ghbot tried to access a network endpoint.

#### Acceptance Criteria

1. IF the report identity or canonical ID is unsupported, THEN the command SHALL return a Click
   usage error that includes the unsupported value and SHALL not perform network access.
2. THE command help and README SHALL document both invocation forms and state that schemas are
   loaded from the installed package.

## Non-Functional Requirements

- Reuse the existing public registry; do not duplicate identifiers, paths, or schema parsing in
  CLI code.
- Preserve every existing command and report-output behaviour.
- Run project checks through `uv run` when implementation begins.
