# Requirements Document

## Introduction

Running multiple ghbot reports currently repeats shared repository discovery for each command. A `combo` meta-processor should scan each repository once, run the reportable built-in processors against that repository, and render their reports together.

## Glossary

- **combo**: The new meta-processor and CLI command that coordinates reportable built-in processors.
- **reportable processor**: One of `SecurityRepoProcessor`, `IssuesRepoProcessor`, or `DriftRepoProcessor`.
- **shared scan**: A single repository-discovery pass that feeds all reportable processors for each discovered repository.
- **combined report**: A report document containing the individual security, issues, and drift report outputs.

## Requirements

### Requirement 1: Provide the combo command

**User Story:** As an operator, I want one command that runs all reportable scans, so that I can review repository posture without repeatedly discovering the same repositories.

#### Acceptance Criteria

1. THE CLI SHALL provide a `combo` command.
2. THE command SHALL run the security, issues, and drift processors for every discovered repository.
3. THE command SHALL NOT run `InfoRepoProcessor`.
4. THE command SHALL use one shared repository scan for its complete execution.
5. FOR EACH discovered repository, THE command SHALL pass the same owner, repository, API client, monitor context, and owner type to each reportable processor.
6. THE command SHALL preserve bounded repository-level concurrency and existing rate-limit propagation behaviour.
7. IF one processor produces a partial repository result, THEN THE command SHALL retain the other processors' results for that repository.

### Requirement 2: Produce a combined JSON report

**User Story:** As an automation author, I want each report's structured result preserved in one JSON document, so that consumers can use the existing report schemas without multiple commands.

#### Acceptance Criteria

1. IF `combo --json` is requested, THEN THE command SHALL emit one JSON object containing separate `security`, `issues`, and `drift` report documents.
2. EACH nested report document SHALL preserve the corresponding standalone JSON report schema, including its summary and repository records.
3. THE JSON report SHALL contain no `info` report section.
4. THE combined JSON report SHALL support the existing output-file option.

### Requirement 3: Produce combined human-readable reports

**User Story:** As an operator, I want readable combined plain and table output, so that all report metrics remain visible in one invocation.

#### Acceptance Criteria

1. IF plain output is requested, THEN THE command SHALL render distinct, labelled security, issues, and drift sections in that order.
2. IF table output is requested, THEN THE command SHALL render distinct, labelled security, issues, and drift table sections in that order.
3. EACH section SHALL retain every line, summary field, row, and column from its standalone renderer.
4. THE combined human-readable output SHALL support the existing output-file option.
5. THE command SHALL retain existing format-selection semantics: default plain output and mutual exclusion of `--plain`, `--table`, and `--json`.

## Non-Functional Requirements

- Reuse existing report renderers rather than duplicating individual report formatting logic.
- Keep the existing standalone commands and their output schemas unchanged.
- Do not add new API calls beyond the processor calls required for security, issues, and drift; repository discovery occurs once.
- Add focused unit tests for one-scan orchestration, processor exclusion, result grouping, output ordering, JSON nesting, format selection, and file output. Run tests with `uv run`.
