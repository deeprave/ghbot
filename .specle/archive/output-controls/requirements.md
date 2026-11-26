# Requirements Document

## Introduction

The `security` command currently has two output concerns mixed together: progress logging while
repositories are scanned, and the final result report printed after scanning completes. Operators
need to choose the final report format for different use cases: plain text for humans, a compact
Markdown table for console readability, and JSON for automation. They also need to write the final
report to a file without redirecting progress logs.

This feature introduces reusable output controls. The `security` subcommand is the first command
to expose these controls, but the CLI-to-processor option path and report-writing model should be
generic enough for future processors and commands to reuse.

## Glossary

- **Output_Format**: The final report encoding requested by the user. Allowed values are
  `"plain"`, `"table"`, and `"json"`.
- **Output_Options**: A generic dictionary passed to every `RepoProcessor` constructor. For this
  feature, it contains `"format": "plain" | "table" | "json"` and may contain future reusable
  options.
- **Output_Target**: The destination for the final result report. If omitted, the report is written
  to stdout. If provided via `--output`, the report is written to that file.
- **Final_Result_Report**: The data emitted after all repository processing completes. This is
  distinct from progress logging and monitor events.
- **Plain_Output**: The previous stacked per-repository format used before the compact table
  change.
- **Table_Output**: The current compact Markdown table format, with fixed-width columns aligned
  for unrendered console output.
- **JSON_Output**: A structured JSON object containing a `"summary"` object and a `"repositories"`
  array.

## Requirements

### Requirement 1: Security-specific format flags

**User Story:** As an operator, I want to choose the final security report format from the
`security` command, so that I can select human-readable or machine-readable output per run.

#### Acceptance Criteria

1. THE `security` subcommand SHALL accept `--plain`, `--table`, and `--json` options.
2. THE format options SHALL apply only to the `security` subcommand, not to the top-level command
   group and not to the `info` subcommand.
3. WHEN no format option is provided, THE `security` subcommand SHALL use `"plain"` as the default
   output format.
4. WHEN `--plain` is provided, THE effective output options SHALL contain `"format": "plain"`.
5. WHEN `--table` is provided, THE effective output options SHALL contain `"format": "table"`.
6. WHEN `--json` is provided, THE effective output options SHALL contain `"format": "json"`.
7. IF more than one of `--plain`, `--table`, and `--json` is provided, THEN THE CLI SHALL fail with
   a usage error before repository processing starts.

### Requirement 2: Generic processor options

**User Story:** As a developer, I want command options passed to processors through a generic
dictionary, so that future processors can reuse output controls without changing constructor
signatures for each new option.

#### Acceptance Criteria

1. THE `RepoProcessor` constructor contract SHALL accept a generic `options` dictionary in addition
   to owner, repository name, GitHub client, and monitor.
2. THE CLI orchestration path SHALL pass the effective command options dictionary to each
   constructed processor.
3. THE `security` command SHALL pass an options dictionary containing at least `"format"` with one
   of `"plain"`, `"table"`, or `"json"`.
4. Existing processors SHALL tolerate an omitted or empty options dictionary by using sensible
   defaults.
5. THE options dictionary SHALL NOT be named or structured in a way that is specific to security
   scanning.

### Requirement 3: Plain final report format

**User Story:** As an operator, I want `plain` output to preserve the previous verbose report, so
that scripts or workflows expecting that display can continue using it.

#### Acceptance Criteria

1. WHEN the effective format is `"plain"`, THE final security report SHALL use the previous
   stacked per-repository format.
2. THE plain report SHALL print the summary stats first:
   - `Repos scanned`
   - `Repos with issues`
   - `Dependabot alerts`
   - `Code scanning alerts`
   - `Secret scanning alerts`
3. THE plain report SHALL include per-repository details only for repositories with at least one
   non-`None`, non-zero alert count.
4. THE plain per-repository section SHALL display Dependabot, code scanning, and secret scanning
   counts as separate labeled lines.
5. THE plain report SHALL display `None` counts as `"N/A"` and zero counts as `0`.

### Requirement 4: Table final report format

**User Story:** As an operator, I want `table` output to use the compact Markdown table, so that
the final report is easier to scan in a terminal while still rendering as Markdown.

#### Acceptance Criteria

1. WHEN the effective format is `"table"`, THE final security report SHALL use the compact
   fixed-width Markdown table after the summary stats.
2. THE table header SHALL contain the columns `Repository`, `Dependabot`, `Scanning`, and
   `Secrets`.
3. THE table columns SHALL be padded so the raw, unrendered console output remains aligned.
4. THE table SHALL include rows only for repositories with at least one non-`None`, non-zero alert
   count.
5. THE table SHALL display `None` counts as `"N/A"` and zero counts as `0`.

### Requirement 5: JSON final report format

**User Story:** As an operator automating ghbot, I want JSON output with stable top-level keys,
so that other tools can consume scan results without parsing text.

#### Acceptance Criteria

1. WHEN the effective format is `"json"`, THE final security report SHALL be valid JSON.
2. THE JSON document SHALL contain a top-level `"summary"` key whose value is an object containing
   the same aggregate stats as the text summary.
3. THE JSON document SHALL contain a top-level `"repositories"` key whose value is an array of
   objects, one object per scanned repository.
4. EACH repository object SHALL include repository identity and the three alert counts.
5. JSON output SHALL preserve `None` values as JSON `null`, not convert them to `"N/A"`.
6. JSON output SHALL include repositories even when they have zero issues, because automation may
   need complete scan coverage.
7. JSON output SHALL be written to the final report destination only, not to progress logs.

### Requirement 6: Final report output target

**User Story:** As an operator, I want to write the final report to a file, so that progress logs
can remain on stderr while the result artifact is captured separately.

#### Acceptance Criteria

1. THE `security` subcommand SHALL accept an `--output` option with a filesystem path.
2. WHEN `--output` is omitted, THE final report SHALL be written to stdout.
3. WHEN `--output` is provided, THE final report SHALL be written to the specified file path.
4. THE `--output` option SHALL affect only the final result report, not progress logging or monitor
   events.
5. THE implementation SHALL write text output using UTF-8.
6. IF the output file cannot be written, THEN THE CLI SHALL fail with a clear error.

### Requirement 7: Preserve progress/output separation

**User Story:** As an operator, I want progress information and final report data kept separate, so
that choosing JSON or file output does not pollute the data stream.

#### Acceptance Criteria

1. Progress logging SHALL continue to use the existing monitor/logging path.
2. The final report SHALL be produced only after repository processing completes.
3. JSON final output SHALL NOT include progress log messages.
4. Writing the final report to a file SHALL NOT redirect stderr logs.
5. The security processor SHALL continue to avoid printing repository-specific progress for
   repositories that do not report issues.
