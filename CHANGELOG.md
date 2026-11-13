# Changelog

All notable changes to ghbot are documented in this file.

## [Unreleased]

### Breaking changes

- Custom processor constructors used with `_main()` must accept the new keyword-only
  `owner_type: str | None = None` argument. Built-in processors default it to
  `None`.

## [0.10.0] - 2026-11-09

### Added

- Added the `drift` command to report default-branch commits since each
  repository's latest stable release, including a PyPI publishing-configuration
  indicator.
