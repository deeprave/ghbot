# Changelog

All notable changes to ghbot are documented in this file.

## [Unreleased]

### Added

- Added explicit repository selection.
- Enhanced `issues` reporting.
- Added combined reports.
- Added versioned report schemas and CLI discovery.
- Added resilient GitHub rate-limit handling.

## [0.30.0] - 2026-11-15

### Added

- Added environment-token authentication through `--env` or `env = true`, using
  `GITHUB_API_TOKEN` without invoking the GitHub CLI.
- Added discovery of private organisation repositories when the configured token can access them.

### Breaking changes

- Custom processor constructors used with `_main()` must accept the new keyword-only
  `owner_type: str | None = None` argument. Built-in processors default it to
  `None`.

### Changed

- Reorganised security, issues, and drift reporting into self-contained mode units with shared
  report styles, while preserving their existing command output and JSON contracts.

## [0.10.0] - 2026-11-09

### Added

- Added the `drift` command to report default-branch commits since each
  repository's latest stable release, including a PyPI publishing-configuration
  indicator.
