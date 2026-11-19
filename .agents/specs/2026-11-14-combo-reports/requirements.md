# Requirements Document

## Introduction

Running multiple ghbot reports currently repeats shared repository discovery for each command. A
`combo` meta-processor should scan each repository once, run every discovered keyed reportable mode
against that repository, and render their reports together.

## Glossary

- **combo**: The new meta-processor and CLI command that coordinates reportable built-in processors.
- **keyed reportable mode**: A discovered `ReportableModeDefinition` returned by
  `combinable_modes()`. It supplies a canonical name, processor factory, collection factory, and
  `combine_key`.
- **combine key**: A unique, zero-padded three-digit string that both makes a mode eligible for
  combination and orders its section without edits to existing modes when a report is inserted.
- **shared scan**: A single repository-discovery pass that feeds all reportable processors for each discovered repository.
- **combined report**: A report document containing one nested report document for every selected
  combinable mode.

## Requirements

### Requirement 1: Provide the combo command

**User Story:** As an operator, I want one command that runs all reportable scans, so that I can review repository posture without repeatedly discovering the same repositories.

#### Acceptance Criteria

1. THE CLI SHALL provide a `combo` command.
2. THE command SHALL obtain its selected modes solely through `combinable_modes()` and SHALL NOT
   maintain a static list of mode names, processor classes, or collections.
3. THE command SHALL run every selected mode's processor for every discovered repository. With the
   current built-ins, this is security, issues, and drift.
4. THE command SHALL NOT run `InfoRepoProcessor`; `info` has no `combine_key` and is therefore
   absent from the selected set.
5. THE command SHALL use one shared repository scan for its complete execution.
6. FOR EACH discovered repository, THE command SHALL pass the same owner, repository, API client,
   monitor context, and owner type to each selected processor.
7. THE command SHALL preserve bounded repository-level concurrency and existing rate-limit
   propagation behaviour.
8. IF one processor produces a partial repository result, THEN THE command SHALL retain the other
   processors' results for that repository.
9. IF `TaskPool` retries a repository task after a secondary rate limit, THEN THE command SHALL
   add at most one result per selected mode for that repository to the combined collections.
10. IF a selected processor raises a non-rate-limit `FatalError` on either its initial attempt or
    a secondary-rate-limit retry, THEN THE command SHALL preserve that error's safe message and
    exit code through the shared task-pool boundary to the CLI.
11. THE command SHALL scan each owner at most once per invocation, treating owner names
    case-insensitively while retaining the first supplied spelling and deterministic order.
12. EACH selected mode SHALL define a unique `combine_key` matching a zero-padded three-digit
    number. The initial keys SHALL be security `010`, issues `020`, and drift `030`.
13. `combinable_modes()` SHALL select and order keyed reportable modes by `combine_key`; adding an
    intervening report SHALL require only its own mode definition and key, not edits to existing
    modes or the combo coordinator.

### Requirement 2: Produce a combined JSON report

**User Story:** As an automation author, I want each report's structured result preserved in one JSON document, so that consumers can use the existing report schemas without multiple commands.

#### Acceptance Criteria

1. IF `combo --json` is requested, THEN THE command SHALL emit one JSON object with one property
   for every selected keyed reportable mode, keyed by that mode's canonical name and ordered by
   `combine_key`.
2. EACH nested report document SHALL preserve the corresponding standalone JSON report schema,
   including its summary and repository records.
3. The current JSON report SHALL contain `security`, `issues`, and `drift` properties, and no
   `info` property.
4. THE combined JSON report SHALL support the existing output-file option.

### Requirement 3: Produce combined human-readable reports

**User Story:** As an operator, I want readable combined plain and table output, so that all report metrics remain visible in one invocation.

#### Acceptance Criteria

1. IF plain output is requested, THEN THE command SHALL render distinct, labelled sections in the
   `combine_key` order returned by `combinable_modes()` (currently security, issues, drift).
2. IF table output is requested, THEN THE command SHALL render the same labelled sections and
   ordering using each mode's table renderer.
3. EACH section SHALL retain every line, summary field, row, and column from its standalone renderer.
4. THE combined human-readable output SHALL support the existing output-file option.
5. THE command SHALL retain existing format-selection semantics: default plain output and mutual exclusion of `--plain`, `--table`, and `--json`.
6. THE command SHALL offer `--labels` and pass it only to the issues-mode collection, preserving
   the existing issues-report label behaviour without changing other modes' options.

## Non-Functional Requirements

- Reuse `CombinedCollectionReport` and existing mode collection renderers rather than duplicating
  individual report formatting logic.
- Keep the existing standalone commands and their output schemas unchanged.
- Do not add new API calls beyond the processor calls required by the selected keyed reportable modes;
  repository discovery occurs once.
- Do not change the distinct primary/secondary rate-limit classification or retry policy; that work
  remains outside this change.
- Add focused unit tests for one-scan orchestration, discovery-derived mode selection, info
  exclusion, combine-key validation and ordering, result grouping, JSON nesting, format selection,
  issues-label forwarding, and file output. Run tests with `uv run`.
