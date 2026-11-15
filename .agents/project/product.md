# Product Overview

ghbot is a command-line tool for scanning GitHub repositories and reporting actionable repository
maintenance information. It supports configured owners and explicitly selected repositories, and
uses processors to gather mode-specific results for human-readable, tabular, and JSON reports.

## Users

- Developers and maintainers responsible for several GitHub repositories.
- Platform teams reviewing repository hygiene, security, issues, or release drift.

## Product constraints

- Repository scans are read-only unless a future feature explicitly authorises mutation.
- Per-repository API failures are represented as partial results where the processor policy allows;
  they are never silently represented as an absence of findings.
- Archived repositories are excluded from scans.
