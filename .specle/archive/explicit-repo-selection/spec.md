# Explicit repository selection

Allow targeted scans through global repeatable `--repo` and single-use `--repos FILE` options. Entries may be `owner/repo` or bare `repo`; each bare entry expands across every configured owner, while a qualified entry is used once.

- Preserve repository-entry and configured-owner order while expanding bare entries; reject a bare
  entry when no owners are configured.
- `--repo` accepts comma-separated entries. `--repos` accepts comma- or line-separated entries,
  ignoring empty entries and lines whose first non-whitespace character is `#`; unreadable files
  are usage errors naming the file.
- Resolve all inline entries before the optional repository-file entries, preserving order within each source.
- Explicit entries are additive. When either explicit option is present, shared discovery used by
  both `run_processor()` and `run_mode()` validates only those repositories and never lists owners.
  Without explicit entries, retain owner-based discovery.
- Use an insertion-ordered dictionary keyed by a case-folded `owner/repo` value to retain the first
  original candidate spelling; warn while skipping every duplicate before validation.
- Validate with `GET /repos/{owner}/{repo}` through `github_api_call()` and yield the existing
  `DiscoveredRepository` metadata and owner type. Skip inaccessible, missing, and archived repos;
  retain retry/skip and rate-limit propagation policy.
- Keep parsing in global CLI configuration and carry the selection representation to the shared
  runner. Mode modules must not parse or select repositories.

Test ordered context, inline/file parsing, explicit-mode listing suppression, validation/error
handling, owner type, and archived filtering through `uv run`.
