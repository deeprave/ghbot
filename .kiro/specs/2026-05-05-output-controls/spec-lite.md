# Spec Lite: Output Controls

## Problem

Add reusable final-output controls. The `security` command should support selecting the final
report format and writing that final report to a file, without mixing progress logs into the
result data stream.

## CLI

```text
ghbot --owner <name> security                 # plain output to stdout
ghbot --owner <name> security --plain         # plain output to stdout
ghbot --owner <name> security --table         # compact Markdown table to stdout
ghbot --owner <name> security --json          # JSON to stdout
ghbot --owner <name> security --json --output results.json
```

- `--plain`, `--table`, and `--json` apply only to `security`.
- The format flags are mutually exclusive.
- `plain` is the default.
- `--output` writes only the final report, not progress logs.

## Generic Options

Command-level options should be passed to every `RepoProcessor` constructor as a generic options
dictionary:

```python
{"format": "plain"}
{"format": "table"}
{"format": "json"}
```

The options path should be reusable for other processors and commands, not named around security.

## Formats

### Plain

Use the previous stacked text format:

```text
Repos scanned:           42
Repos with issues:       12
Dependabot alerts:       34
Code scanning alerts:     8
Secret scanning alerts:   3

owner/repo-name
  Dependabot alerts:       5
  Code scanning alerts:    2
  Secret scanning alerts:  0
```

### Table

Use the current compact fixed-width Markdown table:

```text
Repos scanned:           42
Repos with issues:       12
Dependabot alerts:       34
Code scanning alerts:     8
Secret scanning alerts:   3

|Repository                            | Dependabot | Scanning | Secrets |
|--------------------------------------|------------|----------|---------|
|owner/repo-name                       |           5|         2|        0|
```

### JSON

Use a top-level object with:

- `"summary"`: aggregate stats.
- `"repositories"`: array of objects, one per scanned repository.

JSON should preserve unavailable counts as `null` and include clean repositories.

## Current Uncommitted Changes To Adopt

- Security progress output should reveal repository information only for repositories that report
  issues.
- Security progress should emit `found issues N` instead of `processing started` when issues are
  discovered.
- The compact Markdown table becomes the `table` format, while `plain` remains the default.
