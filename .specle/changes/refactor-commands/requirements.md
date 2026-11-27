# Requirements: Command-line command refactor

## Introduction

ghbot's top-level commands should consistently represent repository scans. The existing `schema`
subcommand only reads installed package resources, so presenting it beside processor-backed scan
commands makes the CLI model inconsistent. Command help also uses mixed verbs and grammatical
patterns for equivalent scan operations.

## Glossary

- **Scanning command**: A top-level command that runs one or more repository processors.
- **Schema invocation**: A non-scanning, leading `--schema` invocation that prints installed
  schema resources.

## Requirements

### Requirement 1: Move schema retrieval out of the command set

**User Story:** As a CLI user, I want the command list to contain only scan operations, while
still being able to retrieve installed schemas directly.

#### Acceptance Criteria

1. THE CLI SHALL replace the `schema` subcommand with a leading `--schema` invocation.
2. THE CLI SHALL support `ghbot --schema REPORT`, `ghbot --schema --id TEXT`, and
   `ghbot --schema --list` with the same schema selection and JSON output semantics as the current
   command.
3. THE CLI SHALL require exactly one schema selector: a report identity, `--id`, or `--list`.
4. THE CLI SHALL treat `--id` and `--list` as schema-only selectors; without leading `--schema`,
   they SHALL remain unknown options rather than becoming general CLI options.
5. THE CLI SHALL no longer recognise `ghbot schema ...` as a command.
6. The leading `--schema` form SHALL not initialise repository scanning or invoke processors.

### Requirement 2: Make scan-command descriptions consistent

**User Story:** As a CLI user, I want help output whose commands use one clear grammatical
pattern.

#### Acceptance Criteria

1. Every processor-backed top-level command SHALL have a description beginning `Scan for`.
2. The remainder of each description SHALL name the command's reported subject in a concise,
   parallel noun phrase.
3. `combo`, `info`, `drift`, `issues`, and `security` descriptions SHALL all follow this pattern.
4. The schema invocation SHALL be described as schema retrieval rather than a scan.

## Boundaries

- This change does not alter schema resource IDs, registry contents, library APIs, report formats,
  authentication, or processor behaviour.
- The leading `--schema` dispatcher is intentionally limited to schema retrieval; it does not make
  `--id` or `--list` globally available.
- The leading-token rule is deliberate: `--schema` must be the first user-supplied argument after
  `ghbot`, allowing the normal command parser to reject schema-only selectors elsewhere.

## Compatibility impact

`ghbot schema ...` is intentionally removed. Script users must change it to the corresponding
leading `ghbot --schema ...` form.
