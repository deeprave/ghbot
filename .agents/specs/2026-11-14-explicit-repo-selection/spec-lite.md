# Explicit repository selection

## Problem

Owner-based discovery scans every accessible repository for each owner. Operators need a targeted, additive repository list from the CLI and files, without owner-list API calls.

## Goal

Add global repeatable `--repo` and `--repos FILE` options. Their entries are additive, resolve in command-line order, and replace owner-based listing whenever either is used.

## Input model

- `--repo` accepts comma-separated `repo` or `owner/repo` entries.
- `--repos FILE` accepts the same entries separated by commas or non-empty lines; lines beginning with optional whitespace followed by `#` are comments.
- A bare name inherits the most recent preceding `--owner`; qualified names do not change that context.
- Bare names without prior owner context are usage errors. Fully qualified lists need no `--owner`.

## Scan model

Explicit selection validates each resolved repository via `GET /repos/{owner}/{repo}` using the shared API wrapper. Valid results become `DiscoveredRepository` records; inaccessible, missing, and archived repositories are skipped under the existing policies. No owner-list endpoint is called in explicit selection mode.

## Verification

Test ordered Click-argument resolution, inline/file parsing, mixed sources, no owner-list discovery in explicit mode, validation metadata/owner type, errors, and archived filtering. Run Python quality gates through `uv run`.
