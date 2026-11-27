# Summary: Streamline schema CLI invocation

## Summary

ghbot now retrieves packaged schemas through a leading `--schema` invocation, leaving the command
list exclusively for repository scans.

## Outcome

Schema lookup is clearly separated from processor-backed commands, while scan help uses one
consistent `Scan for …` description pattern.

## What changed

- Replaced `ghbot schema …` with leading `ghbot --schema` forms.
- Standardised scan command descriptions and schema documentation.
- Updated pending activity and settings requirements to use the supported schema form.

## Key decisions and limits

`--schema` must be the first argument after `ghbot`; `--id` and `--list` remain schema-only
selectors.
